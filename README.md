# ebacame
E-bike BAtteries Charging Made Easy

## Overview

This programm sets up an easy to use Server that makes charging e-bike batteries conservatively easy. Usually, Li-Ion batteries should be charged up to 80% full charge in order to make them last longer. However, every thenth time they should be charged to 100% full charge to activate the cell balancing system. Thats were things usually start to became complicated. ebacame is designed to make this easier by
- switching the charger off when 80% state is reached (except explicitely told to charg up to 100%)
- count the number of 80%-charges and automatically charge 100% if the battery was charged 10 times in a row up to 80%
