\# Quiet Mode Integration



Quiet Mode is a custom Home Assistant integration that allows reducing

the volume of multiple media players at once and restoring them later.



\## Features

\- Enable quiet mode with a target volume

\- Disable quiet mode and restore original volumes

\- Works with multiple `media\_player` entities



\## Services



\### quiet\_mode.enable

Lowers volume of selected media players.



\*\*Service data:\*\*

\- `entity\_id`: list of media\_player entities

\- `quiet\_volume`: float between 0.0 and 1.0



\### quiet\_mode.disable

Restores original volumes for selected media players.



\## Example Usage



```yaml

service: quiet\_mode.enable

data:

&nbsp; entity\_id:

&nbsp;   - media\_player.kitchen

&nbsp;   - media\_player.living\_room

&nbsp; quiet\_volume: 0.12



