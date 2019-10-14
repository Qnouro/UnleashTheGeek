# UnleashTheGeek

# Table of Contents 

1.[About](#about)  

2.[The hackathon's goal](#the-hackathons-goal) 
  1. [Strategies](#strategies)
  2. [Radar placement](#radar-placement)
  3. [Mining](#mining)
  4. [Traps](#traps)
  
3.[What could have been improved](#what-could-have-been-improved)
  1. [Movement algorithm](#movement-algorithm)
  2. [Simplex method](#simplex-method)
  3. [Custom algorithm](#custom-algorithm)
  4. [The wall problem](#the-wall-problem)



## About

This repository contains the code used on the 10 days hackathon named "Unleash The Geek" proposed by Amadeus starting on October 4th 2019.
This code allowed me to peak at rank #57, and ending the competition at rank #169 out of 2166 participants.

## The hackathon's goal

The hackathon is a bot programming competition. Each player has 5 bots to command. A map containing hidden Amadeusium is generated at the beginning of the game, and both players can use radars to detect and mine them. The players also have traps at their disposal in order to destroy enemy bots when triggered. The traps can only be triggered by digging or if a neighbooring trap explodes; stepping on them does not trigger them.

## Strategies

The strategy used relied heavily on disabling the enemy bots, and having an optimized mining.

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

### Movement algorithm

I managed to come up with a movement algorithm (but sadly didn't have enough time to implement it) in order to tackle the second part of the problem. The idea is to keep a safe distance between the bots by realizing the following condition: 
<a href="https://latex.codecogs.com/gif.latex?manhattan\_distance(bot_i,%20bot_j)%20\geq%203;%20i%20\neq%20j" target="_blank"><img src="https://latex.codecogs.com/gif.latex?manhattan\_distance(bot_i,%20bot_j)%20\geq%203;%20i%20\neq%20j" /></a>.

#### Simplex method

The first idea would be to solve a simplex problem. We define a direction vector which corresponds to the direction the bot is heading to for the next turn, to which we add a deviation. We are looking forward to minimizing the sum of all deviations in a turn. As the manhattan distance relies on the absolute value, we can still trick the inequations and end up with a linear problem.

This solution however is not suitable for our case due to the time limitations (less than 50ms for every turn).

#### Custom algorithm

Another method would be to order the bots based on their y coordinate.
Starting from the first bot, if he doesn't verify the condition with the 2nd bot, we deviate him to the top of the map. We do the same for all the other bots. However, deviating the ith bot would force us to reverify all the previous bots as they might not verify the condition anymore. We end up with several passes, which the complexity is squared.
If the first bot cannot go up anymore, we can either choose to reduce its "speed" (by travelling less than 4 cells) and keep deviating, or we could redo the algorithm starting from the last bot, and deviating downward.
In this process, we do not consider the bots that are digging as they cannot move (and hence, cannot deviate). In this case, we just have to cut the algorithm(e.g: if the 3rd bot is mining, we apply our algorithm on the 2 first bots and the 2 last bots). 
Another problematic case is if the 2nd and 4th bot are static and are blocking the 3rd bot. In this case, we are forced to choose a bot to deviate from and another to get close to. Despite risking exploding, it shall still be on average more beneficial to take the risk from time to time.

### The wall problem

As stated earlier, the previous algorithm does not tackle the bomb wall problem. For the latter, a good idea would be to go trigger the wall and trade with the enemy who has already wasted several rounds building the wall. This idea wasn't digged in further due to lack of time.
