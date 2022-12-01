[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

# LoL in-house bot
A Discord bot to handle League of Legends in-house games, with role queue, matchmaking, and rankings.

## Note

This is a fork of [inhouse_bot](https://github.com/mrtolkien/inhouse_bot). The original project is no longer maintained, so I'm using this repo to develop new features.

## Running the app
 
 1. Install [Docker](https://docs.docker.com/get-docker/)
 2. Activate your bot on the Discord developer portal and give it the Server Members privileged intent: [Video](http://www.youtube.com/watch?v=TksVS8PE2fw    "Youtube Video")
 
 3. In github, go: profile in top right -> Settings -> Developer settings -> Personal Access Tokens -> Generate new token:
    
    a. Name to indicate personal access token
    
    b. Select ```(write:packages and read:packages and delete:packages)```
    
    c. Generate token
    
    d. Copy token value
 
 4. In terminal do the following:
    
    a. export CR_PAT=```{your_token_value}```
    
    b. ```echo $CR_PAT | docker login ghcr.io {github_user_name} --password-stdin```
    
    c. After that command, you should get (login succeeded)

5. In docker.compose yml, replace all the values as needed:
    
    a. INHOUSE_BOT_TOKEN = ```{token of discord bot}```
    
    b. INHOUSE_BOT_RIOT_API_KEY = ```{riot api key}```
    
    c. POSTGRES_PASSWORD: = ```{postgres password}``` -- can be anything.
    
    d. And for all the emojis copy over the values of the pictures you get from your discord server
 
 6. ```docker compose build ```

 7. ```docker compose up -d```, at this point the application should be running

# How Algorithm Works
1. Generate all possible teams with players in queue
2. Get each players summoner rift rank (Solo/Duo)
3. Get rank value for Team A and Team B
4. Attempt to find the smallest difference amongst Team A and Team B
5. Do this for all teams generated

**Potential Drawbacks To This Algorithm**:
- **Smurfs**: Smurfs can be detrimental to this system, so during the verification stage make sure each player is using main account
- **Off Roles**: The algorithm assumes you perform at your rank level in potentially all roles, to minimize this, encourage players to play roles they would play in summoners rift
- **No ranked games in current season**: If said player is taking an "off" year, but this player was "high elo" before then you could have unfair teams, so ideally the player base plays enough to justify their rank

# Basic use
```
# Enter the channel’s matchmaking queue
!queue mid
>>> 🇲

# Accept games by reacting to the ready check message
>>> ✅✅✅✅✅✅✅✅✅✅✅
>>> Game 1 has started

# Games can be scored with !won
!won
>>> ✅✅✅✅✅✅✅
>>> Game 1 has been scored as a win for blue and ratings have been updated

# Champion played can be added with !champion
!champion riven
>>> Champion for game 1 set to Riven for Tolki
```

# Queue features
- `!queue role` puts you in the current channel’s queue for the given role

- `!queue role @user other_role` duo queues you together with the tagged player in the current channel

- `!leave` removes you from the channel’s queue for all roles

- `!won` scores your last game as a win for your team and waits for validation from at least 6 players from the game

- `!champion champion_name [game_id]` informs which champion you used for winrate tracking
    - If you don’t supply the `game_id`, it will apply to your last game

- `!cancel` cancels your ongoing game, requiring validation from at least 6 players in the game

# Admin features
- `!admin reset @user` removes the user from all queues (his name or discord ID work too)

- `!admin reset #channel` resets the queue in the given channel (or the current channel with `!admin reset`)

- `!admin won @user` scores the game as a win for the user without asking for validation

- `!admin cancel @user` cancels the ongoing game of the specified user
