import levels
__all__ = [ 'state' ]


class State( object ):

    STATE_PAUSE, STATE_PLAY, STATE_WIN, STATE_OVER = range(4)

    PLAYER_ROLLING, PLAYER_FARTING = range(2)

    def __init__( self ):

        # current score
        self.score = 0

        # current level
        self.level = None

        # current level idx
        self.level_idx = None

        # time
        self.time = 0

        # eated coins
        self.coins = 0

        # farts
        self.farts = 0

        # game state
        self.game_state = self.STATE_PAUSE

        # player state
        self.player_state = self.PLAYER_ROLLING

        self.start_level = 0

    def reset( self ):
        self.score = 0
        self.level = None
        self.level_idx = None
        self.state = self.STATE_PAUSE
        self.coins = 0

    def set_level( self, l ):
        self.level_idx = l
        self.level = levels.levels[l]
        self.coins = 0
        self.farts = 0
        self.time = self.level.time

state = State()
