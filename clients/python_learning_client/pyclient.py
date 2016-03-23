from __future__ import print_function
from ontology import *
import logging
import numpy as np

class PyClient:

    def __init__(self, agent, logger):
        self.commState = CommState.START
        self.game = GVGame()
        self.avatar = GVGAvatar()
        self.numGames = 0
        self.logger = logger
        self.agent = agent

    def writeToPipe(self, line):
        sys.stdout.write(line + os.linesep)
        sys.stdout.flush()


    def listen(self):
        """
        This process is continuously listening for commands from the GVGAI engine.
        """
        messageIdx = 0
        line = "start"
        while (line != ""):

            #Read the line
            line = sys.stdin.readline()
            self.commState = self.processCommLine(line)
            self.processLine(line)

            #if self.commState == CommState.INIT: #In this state, we are still receiving init information
            #if self.commState == CommState.INIT_END: #In this state, we are still receiving init information
            #if self.commState == CommState.ACT: #In this state, we are receiving state information for ACTING
            #if self.commState == CommState.ACT_END: #In this state, we have finished receiving information for ACTING.
            #if self.commState == CommState.ENDED: #In this state, the game has ended, and we are receiving the last state.
            #if self.commState == CommState.ENDED_END: #In this state, the game has ended, and we have received all final state info.


            if self.commState == CommState.INIT_END:
                #New game starts, time for some initialization work.
                self.agent.init(self.game, self.avatar, self.game.remMillis)
                self.writeToPipe("INIT_DONE.")


            if self.commState == CommState.ACT_END:
                #This is the place to think and return what action to take.
                action = self.agent.act(self.game, self.avatar, self.game.remMillis)
                self.writeToPipe(action)


            if self.commState == CommState.ENDED_END:
                #A game has finished. Time to analyze what happened.
                self.agent.end(self.game, self.avatar, self.game.remMillis)

                #Here, we need to reset game and avatar back
                self.game = GVGame()
                self.avatar = GVGAvatar()

                self.writeToPipe("GAME_DONE.")

            messageIdx += 1




    def processCommLine(self, line):

        if "INIT-END" in line:
            splitLine = line.split(" ")
            self.game.remMillis = int(splitLine[1])
            return CommState.INIT_END

        if "ACT-END" in line:
            splitLine = line.split(" ")
            self.game.remMillis = int(splitLine[1])
            return CommState.ACT_END

        if "ENDGAME-END" in line:
            splitLine = line.split(" ")
            self.game.remMillis = int(splitLine[1])
            return CommState.ENDED_END


        if "INIT" in line:
            self.numGames+=1
            splitLine = line.split(" ")
            self.isTraining = (splitLine[1] == 'true')
            return CommState.INIT

        if "ACT" in line:
            return CommState.ACT

        if "ENDGAME" in line:
            return CommState.ENDED

        return self.commState


    def processLine(self, line):

        """
        This function process a line received.
        """

        splitLine = line.split("#")
        lineType = splitLine[0]


        if lineType == "Game":
            self.game.score = float(splitLine[1])
            self.game.gameTick = int(splitLine[2])
            self.game.gameWinner = splitLine[3]
            self.game.gameOver = (splitLine[4] == 'true')

            if len(splitLine) > 6: # It will only be >6 in the init case.
                self.game.worldDim = [int(splitLine[5]), int(splitLine[6])]
                self.game.blockSize = int(splitLine[7])


        elif lineType == "Actions":
            actions = splitLine[1].split(",")
            for act in actions: self.avatar.actionList.append(act)

        elif lineType == "Avatar":
            self.avatar.position = [float(splitLine[1]), float(splitLine[2])]
            self.avatar.orientation = [float(splitLine[3]), float(splitLine[4])]
            self.avatar.speed = float(splitLine[5])
            self.avatar.lastAction = splitLine[6]

            if len(splitLine[7]) > 0:
                #We have resources:
                resources = splitLine[7].split(";")
                for r in resources:

                    key = int(r.split(",")[0])
                    val = int(r.split(",")[1])

                    self.avatar.resources[key] = val

        elif lineType[0] == 's': #Observation Grid
            spriteID = int(lineType[1:])
            bitData = splitLine[1].split(",")

            nRows = len(bitData)
            nColumns = len(bitData[0])

            spriteBitMap = np.ndarray(shape=(nRows, nColumns), dtype=int)

            for r in range(0,nRows):
                row = bitData[r]
                for c in range (0, nColumns):
                    spriteBitMap[r][c] = int(row[c])

            self.game.grid[spriteID] = spriteBitMap

        #print(self.game)

        return False


if __name__=="__main__":
    logging.basicConfig(filename='play.log', level=logging.INFO)
    import sys
    import importlib
    mypackage, myclass = sys.argv[1].split(".")
    m = importlib.import_module(mypackage)
    # get the class, will raise AttributeError if class cannot be found

    try:
        c = getattr(m, myclass)
        agent = c(logging.getLogger(myclass))
        pyClient = PyClient(agent = agent, logger=logging.getLogger("PyClient"))
        pyClient.listen()
    except Exception as e:
        logging.exception("Error in client")