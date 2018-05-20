
# No accounting yet. Only projects on-going and their scope
# ---------------------------------------------------------
# initialization of companies
#
# Defined in constants the following values:
#  - how many rounds max the game is played (1 round = 2 weeks)
#  - what is the winning cash amount (when reached, game halts
#    and company claimed winner)

# This script implements the so called 'business game'
# where companies make Software Projects. They
# can choose to concentrate at each turn
# - on features ('code ahead')
# - on training (making workers more skillful)

# Goal of MVP: take turns, do not yet hire. Just make the projects completed.
# Gain revenue, and initiate a new project.
# Tally the global Rounds in game.

weeksPerRound = 2
limRounds = 5 * (52 / weeksPerRound)  # 5 years max game time
limRevenue = 100000  # Winning cash amount (limit)

rounds = 0           # Current round, 0 start

INIT_CASH = 1000     # Initial cash at hand for each company
PARTICIPANTS = 3     # Number of companies used

coCash = []         # Companies' financial (cash at hand)
coPersonnel = []    # Number of developers (we do not count management at all)
coChoice = []       # This round's (ongoing) choice of either 'F' or 'T'
prScope = []
prCash = []


def testBasics():
    print('Initialization of companies...')
    initializeGame()


# The board meeting for company i
# Decisions are made in this function
def boardMeeting(i):
    return True


def initializeGame():
    # Set up the cash for all companies
    for i in xrange(1, PARTICIPANTS):
        coCash.append(INIT_CASH)
    print('Now the cash is set up for all companies. Below list:')
    # Print out all companies cash (after initialized)
    for t in xrange(1, PARTICIPANTS):
        print('')
    print('Truth checking, the highRevenue() should be the number below:')
    print(INIT_CASH)
    print('...and the max is now:')
    print(highRevenue())


def highRevenue():
    return max(coCash)


initializeGame()
print('=====================')
print('Let the games begin!')
print('=====================')

# TODO: Add the "winner" limit also: company reaching 'limRevenue'
while ((rounds < limRounds) and (highRevenue() < limRevenue)):
    limRevenue += 1000
    # Ensure that the loop discontinues at some point


# Convert game rounds => years, based on the constant
def gameClockYear(rs):
    return rs / (52 / weeksPerRound)
