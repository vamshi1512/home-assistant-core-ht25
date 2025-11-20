"""DataUpdateCoordinator for the Public Transport integration."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
import logging
import random

from aiohttp import ClientError, ClientResponseError

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .gtfs import gtfs_realtime_pb2
from .models import Departure, GtfsConfig, StopTimeInfo, TripData

_LOGGER = logging.getLogger(__name__)

PublicTransportData = dict[str, list[Departure]]


class PublicTransportDataUpdateCoordinator(DataUpdateCoordinator[PublicTransportData]):
    """Coordinator that retrieves GTFS-RT data."""

    config: GtfsConfig
    last_fetch: datetime | None
    last_trip_count: int
    trips: dict[str, TripData]
    all_stop_ids: set[str]

    def __init__(self, hass: HomeAssistant, config: GtfsConfig) -> None:
        """Initialize the coordinator."""

        self.config = config
        self._session = async_get_clientsession(hass)
        self.last_fetch = None
        self.last_trip_count = 0
        self.trips = {}
        self.all_stop_ids = set()

        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"{DOMAIN} coordinator",
            update_interval=config.scan_interval,
        )

    async def _async_update_data(self) -> PublicTransportData:
        """Fetch GTFS-RT data and compile departures."""

        headers: dict[str, str] = {}
        if self.config.api_key_header_name and self.config.api_key_value:
            headers[self.config.api_key_header_name] = self.config.api_key_value

        try:
            async with self._session.get(self.config.feed_url, headers=headers, raise_for_status=True) as response:
                payload = await response.read()
        except ClientResponseError as err:
            raise UpdateFailed(f"HTTP error {err.status}") from err
        except ClientError as err:
            raise UpdateFailed(f"Network error: {err}") from err

        feed_message = gtfs_realtime_pb2.FeedMessage()
        try:
            feed_message.ParseFromString(payload)
        except Exception as err:
            raise UpdateFailed(f"Could not parse GTFS-RT payload: {err}") from err

        departures_by_stop: defaultdict[str, list[Departure]] = defaultdict(list)
        trips: dict[str, TripData] = {}
        all_stop_ids: set[str] = set()

        now = dt_util.utcnow()
        stop_filter = set(self.config.stop_ids)
        route_filter = self.config.route_ids
        trip_count = 0

        for entity in feed_message.entity:
            trip_update = getattr(entity, "trip_update", None)
            if not trip_update or not trip_update.stop_time_update:
                continue

            trip_count += 1
            route_id = trip_update.trip.route_id or "unknown"
            trip_id = trip_update.trip.trip_id or entity.id

            if route_filter and route_id not in route_filter:
                continue

            headsign = getattr(trip_update.trip, "trip_headsign", None)
            vehicle_id = trip_update.vehicle.id if trip_update.HasField("vehicle") else None

            trip_stops: dict[str, StopTimeInfo] = {}

            for update in trip_update.stop_time_update:
                stop_id = update.stop_id
                all_stop_ids.add(stop_id)

                arrival_event = update.arrival if update.HasField("arrival") else None
                departure_event = update.departure if update.HasField("departure") else None

                event = arrival_event or departure_event
                if event is None or not event.time:
                    continue

                arrival_time = dt_util.utc_from_timestamp(event.time)
                delay_seconds = event.delay if event.delay else 0

                scheduled_epoch = event.time - delay_seconds if delay_seconds else event.time
                scheduled_time = dt_util.utc_from_timestamp(scheduled_epoch)

                stop_headsign = getattr(update, "stop_headsign", None)
                sequence = update.stop_sequence if update.HasField("stop_sequence") else None  # type: ignore[attr-defined]
                platform: str | None = None

                trip_stops[stop_id] = StopTimeInfo(
                    stop_id=stop_id,
                    sequence=sequence,
                    arrival_time=arrival_time,
                    scheduled_time=scheduled_time,
                    delay_seconds=delay_seconds,
                    platform=platform,
                )

                if stop_id in stop_filter:
                    departure = Departure(
                        stop_id=stop_id,
                        route_id=route_id,
                        headsign=stop_headsign or headsign,
                        scheduled_time=scheduled_time,
                        arrival_time=arrival_time,
                        delay_seconds=delay_seconds,
                        vehicle_id=vehicle_id,
                    )

                    departures_by_stop[stop_id].append(departure)

            if trip_stops:
                trips[trip_id] = TripData(
                    trip_id=trip_id,
                    route_id=route_id,
                    headsign=headsign,
                    stops=trip_stops,
                )

        max_departures = self.config.max_departures
        for stop_id in list(departures_by_stop):
            departures_by_stop[stop_id].sort(key=lambda dep: dep.arrival_time)
            departures_by_stop[stop_id] = departures_by_stop[stop_id][:max_departures]

        # Only include stops that actually had departures in this refresh to
        # align with tests and avoid implying empty results as data.

        self.last_fetch = now
        self.last_trip_count = trip_count
        self.trips = trips
        self.all_stop_ids = all_stop_ids

        return dict(departures_by_stop)

    def compute_next_buses(
        self,
        from_stop_id: str,
        to_stop_id: str,
        limit: int = 2,
        only_buses: bool = True,
    ) -> list[dict[str, object]]:
        """Compute next buses for a from→to pair from current trips.

        When demo_random is enabled, produce synthetic departures 15–25 minutes
        from now, with random delays and durations.
        """

        if self.config.demo_random:
            now = dt_util.utcnow()
            rows: list[dict[str, object]] = []
            for _ in range(limit):
                dep_in = random.randint(15, 25)
                delay_min = random.randint(0, 5)
                duration_min = random.randint(10, 20)
                real_dep = now + timedelta(minutes=dep_in)
                planned_dep = real_dep - timedelta(minutes=delay_min)
                arrival = real_dep + timedelta(minutes=duration_min)
                route_num = random.randint(1, 8)
                route_id = f"R{route_num}"
                rows.append(
                    {
                        "planned_dep": dt_util.as_local(planned_dep).isoformat(),
                        "real_dep": dt_util.as_local(real_dep).isoformat(),
                        "arrival": dt_util.as_local(arrival).isoformat(),
                        "duration_min": duration_min,
                        "line": route_id,
                        "platform": "Position B",
                        "delay_min": delay_min,
                    }
                )
            return rows

        if not self.trips:
            return []

        now = dt_util.utcnow()
        candidates: list[tuple[datetime, dict[str, object]]] = []

        for trip in self.trips.values():
            if only_buses and not trip.route_id.upper().startswith("R"):
                continue

            from_info = trip.stops.get(from_stop_id)
            to_info = trip.stops.get(to_stop_id)
            if not from_info or not to_info:
                continue

            if from_info.arrival_time < now:
                continue

            if (
                (from_info.sequence is not None and to_info.sequence is not None and from_info.sequence >= to_info.sequence)
                or to_info.arrival_time <= from_info.arrival_time
            ):
                continue

            duration_min = int(round((to_info.arrival_time - from_info.arrival_time).total_seconds() / 60))
            delay_min = int(round(from_info.delay_seconds / 60))

            row = {
                "planned_dep": dt_util.as_local(from_info.scheduled_time).isoformat(),
                "real_dep": dt_util.as_local(from_info.arrival_time).isoformat(),
                "arrival": dt_util.as_local(to_info.arrival_time).isoformat(),
                "duration_min": max(duration_min, 0),
                "line": trip.route_id,
                "platform": from_info.platform,
                "delay_min": max(delay_min, 0),
            }

            candidates.append((from_info.arrival_time, row))

        candidates.sort(key=lambda item: item[0])
        return [row for _, row in candidates[:limit]]
