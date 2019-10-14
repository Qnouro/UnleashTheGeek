# UnleashTheGeek

## About

This repository contains the code used on the 10 days hackathon named "Unleash The Geek" proposed by Amadeus starting on October 4th 2019.
This code allowed me to peak at rank #57, and ending the competition at rank #169 out of 2166 participants.

## The hackathon's goal

The hackathon is a bot programming competition. Each player has 5 bots to command. A map containing hidden Amadeusium is generated at the beginning of the game, and both players can use radars to detect and mine them. The players also have traps at their disposal in order to destroy enemy bots when triggered. The traps can only be triggered by digging or if a neighbooring trap explodes; stepping on them does not trigger them.

## Strategies

The strategy used relied heavily on 

### Radar placement

The radars are placed following a given position list that maximizes the vision on the map, in order to locate as much ores as fast as possible. When a position is deemed risky, a neighbooring one is generated. If no neighbooring cell is safe, or the pre-made list is emptied, a new position is generated by either taking the farthest ore's position or by generating a random position.

The new position has to always be safe, and far from the previously placed radars.

The idea behind taking the farthest ore's position comes from noticing that ores are usually packed up and discovering some ores usually means that more ores are nearby.

### Mining

The closest bot to the first radar position will be in charge of placing it. During this time, the 4 other bots will go dig in some given positions near the High Quarter.

In order to optimize the mining process, we have to place the radars as fast as possible. For this reason, the bots can be assigned the "radar bot" role when a radar is available and they are in the High Quarter.

If no ore is located, the bots will go back to the first plan, waiting for more ores to be located. 

### Traps

Traps are placed if we aren't in the early or late game phases, and if the number remaining located ores is very small.

The traps' positions are the positions where the bot was initially heading to dig ores.

When detonating, the traps could cause a chain reaction. This way, at every turn, we could simulate if an explosion would be beneficial for us. The process worked on 2 stages. At first, we simulate the detonation of existing traps, and check if a bot is nearby to detonate them. However, if a bot is holding a trap, we could simulate if placing it in any nearby position would be beneficial, by simulating the enemy bots' movements. This simulation would try to predict 2 turns in advance while the previous one would predict 1 turn in advance.

## What could have been improved

While the program gave some very satisfactory results, it struggled a lot against bots that would "wall" the first column of the map with bombs, or against other aggressive programs. For these reasons, the bots' movements could be improved if we see that the enemy is also using traps.

### Dodge algorithm

I managed to come up with a dodging algorithm (but sadly didn't have enough time to implement it) in order to tackle the second part of the problem. The idea is to keep a safe distance between the bots by realizing the condition $manhatan_distance(bot_i, bot_j) >= 3; i != j$. The process would go into multiple passes over the bots. # TODO: explain the algorithm
