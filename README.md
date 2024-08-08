# ebacame
E-bike BAtteries Charging Made Easy

## Overview

### idea
This programm sets up an easy to use Server that makes conservatively charging e-bike batteries easy. Usually, Li-Ion batteries should be charged up to 80% of full capacity in order to make them last longer. However, every thenth time they should be charged to 100% to activate the cell balancing system. Thats were things usually start to become complicated. ebacame is designed to make this easier by
- switching the charger off when 80% state is reached (except explicitly told to charge up to 100%)
- count the number of 80%-charges and automatically charge 100% if the battery was charged 10 times in a row up to 80%

### things needed
ebacame currently needs
- a mystrom socket to remotely switch on and off the charger and to measure the transmitted energy. The mystrom socket must be connect to the local WIFI
- a raspi computer to run the server
- any device to use the web-UI (smartphone, PC, whatever)
### current state
ebacame works, but it needs some parameters which depend on the battery and the charger. These are hard-coded at the moment. Obviously usefull extensions are
- automatically adapt to battery capacity and charger
- handle more than 1 battery
