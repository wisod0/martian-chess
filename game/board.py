from game.enum import PlayerID


class MartianChessBoard:
    width: int      # The width of the board
    height: int     # The height of the board
    board: list     # Stores the current board state
    players: list   # List of players who are playing on this board
    points: dict    # Maps playerID to number of points
    last_move: dict # Stores the last move made (player, from_x, from_y, to_x, to_y, crosses)


    def __init__(
        self, 
        width: int | None = 4,  # Width of the board, defaults to 4
        height: int | None = 8, # Height of the board, defaults to 8
        default_setup: bool | None = True,  # Whether or not to automatically place the default pieces for a 2 player game.
        custom_players: list | None = None  # Option to provide your own list of player IDs
    ):
        # Set board parameters
        self.width = width
        self.height = height
        self.last_move = {}
        self.points = {}

        # Add players
        self.players = [PlayerID.TOP, PlayerID.BOTTOM]  # Default players
        if custom_players:
            self.players = custom_players

        # Initialize board
        self.default_pieces = default_setup
        self.reset_board()


    def place(self, piece, x, y):
        """Places the given piece at the requested XY coordinates. (0=none, 1=pawn, 2=drone, 3=queen)"""
        self.board[x][y] = piece
    

    def get_space(self, x, y):
        """Gets the value of a specific space of the board, returns -1 if out of bounds."""
        if not (x >= 0 and y >= 0 and x < self.width and y < self.height):
            return -1
        return self.board[x][y]


    def _place_default_pieces(self):
        """Manually places the pieces for the default game"""
        pieces_to_place = [(3,0,0),(3,1,0),(3,0,1),(2,2,0),(2,1,1),(2,0,2),(1,1,2),(1,2,2),(1,2,1)]
        # Place top left pieces
        for piece in pieces_to_place:
            self.place(piece[0],piece[1],piece[2])
        # Place bottom right pieces
        w,h = self.width-1, self.height-1
        for piece in pieces_to_place:
            self.place(piece[0],w-piece[1],h-piece[2])


    def get_controlled_pieces(self, player: str):
        """Returns a list of pieces that this player has control over in the format (piece type, x, y)"""
        focus_x1, focus_y1, focus_x2, focus_y2 = self.get_focus_area(player)
        # Find pieces within this focus
        pieces = []
        for x in range(focus_x1, focus_x2 + 1):
            for y in range(focus_y1, focus_y2 + 1):
                piece = self.get_space(x, y)
                # Only add if it's not empty
                if piece > 0:
                    pieces.append((piece, x, y))
        return pieces
    

    def check_piece_ownership(self, player, x, y):
        """Check if given player owns piece at x,y"""
        focus_x1, focus_y1, focus_x2, focus_y2 = self.get_focus_area(player)
        return (x >= focus_x1 and x <= focus_x2 and y >= focus_y1 and y <= focus_y2)

    
    def get_focus_area(self, player: str):
        focus_x1, focus_y1, focus_x2, focus_y2 = 0,0,self.width-1,self.height-1
        if player == PlayerID.TOP:
            # Focus on top half of board
            focus_y2 = (self.height/2)-1
        elif player == PlayerID.BOTTOM:
            # Focus on bottom half of board
            focus_y1 = self.height/2
            focus_y2 = self.height-1
        return int(focus_x1), int(focus_y1), int(focus_x2), int(focus_y2)


    def get_piece_options(self, player, piece_type, x, y):
        """Determines what options a piece has based on it's type, location and owner player"""
        options = []
        moves = []

        # Determine possible moves
        if piece_type == 1:
            # Pawn
            direct_moves = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
            for move in direct_moves:
                moves.append((x + move[0], y + move[1]))
        elif piece_type == 2:
            # Drone
            directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
            for dir in directions:
                cx, cy = x, y
                for i in range(2):
                    cx = cx + dir[0]
                    cy = cy + dir[1]
                    if self.get_space(cx, cy) < 0: # If out of bounds, stop now
                        break
                    moves.append((cx, cy))
                    if self.get_space(cx, cy) > 0: # If there's a piece here, stop after adding to moves
                        break
        elif piece_type == 3:
            # Queen
            directions = [(1, 0), (-1, 0), (0, 1), (0, -1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
            for dir in directions:
                cx, cy = x, y
                while True:
                    cx = cx + dir[0]
                    cy = cy + dir[1]
                    if self.get_space(cx, cy) < 0: # If out of bounds, stop now
                        break
                    moves.append((cx, cy))
                    if self.get_space(cx, cy) > 0: # If there's a piece here, stop after adding to moves
                        break

        # Enumerate possible moves
        for move in moves:
            cx, cy = move[0], move[1]

            if self.last_move.get("crosses") == True: # Check for move rejection
                if self.last_move["to_x"] == x and self.last_move["to_y"] == y and self.last_move["from_x"] == cx and self.last_move["from_y"] == cy:
                    continue # Exclude illegal move

            if self.get_space(cx, cy) == 0: # Is it an empty space?
                options.append((cx, cy))

            elif self.can_player_take(player, cx, cy): # Can we take enemy piece?
                options.append((cx, cy))

            elif self.can_field_promote(player, x, y, cx, cy): # Can we do a field promotion?
                options.append((cx, cy))

        return options

    
    def get_player_options(self, player: str):
        """Returns all of the options that a player has in a list of tuples formatted as (piece x, piece y, to x, to y)"""
        pieces = self.get_controlled_pieces(player)
        options = []
        for piece in pieces:
            # Add the options for this piece
            piece_options = self.get_piece_options(player, piece[0], piece[1], piece[2])
            for option in piece_options:
                options.append((piece[1], piece[2], option[0], option[1]))
        return options


    def can_player_take(self, player, x, y):
        """Returns true if the given player can take the piece at x,y. Checks for ownership and out of bounds."""
        if self.get_space(x, y) < 0: # Out of bounds check
            return False
        if self.check_piece_ownership(player, x, y): # Ownership check
            return False
        return True
    

    def can_field_promote(self, player, piece_x, piece_y, to_x, to_y):
        """Checks if the player can field promote by moving piece to another piece"""
        if not self.check_piece_ownership(player, piece_x, piece_y) or not self.check_piece_ownership(player, to_x, to_y):
            # If player doesn't own both pieces, abort
            return False
        
        pieceA = self.get_space(piece_x, piece_y)
        pieceB = self.get_space(to_x, to_y)
        if pieceA == 1 and pieceB == 2 or pieceA == 2 and pieceB == 1:
            # Field promotion to queen possible
            return 3
        if pieceA == 1 and pieceB == 1:
            # Field promotion to drone possible
            return 2
        

    def is_game_over(self):
        """Scans the board state and determines if the game is over, if so, returns playerID of winner"""
        game_over = False
        for player in self.players:
            pieces = self.get_controlled_pieces(player)
            if len(pieces) == 0:
                game_over = True # Game is over
        if not game_over:
            return False # Let the game go on.
        
        # Figure out who won
        max_points = max(self.points.values()) # Calculate max points a player has
        winners = []
        for player, player_points in self.points.items():
            if player_points >= max_points:
                winners.append(player)

        assert len(winners) > 0 # Sanity check
        if len(winners) == 1:
            return winners[0] # Congratulations!
        
        # Tie breaker
        if len(winners) > 1:
            winner = self.last_move.get("player") # In the event of a tie, the person who made the game end wins.
            if not winner:
                raise Exception("No winner? (Did the board start empty?)")
            return winner # Congratulations!
        

    def reset_board(self):
        """Resets the board back to its original state"""
        # Set default board state
        self.board = [[0 for y in range(self.height)] for x in range(self.width)]
        if self.default_pieces:
            self._place_default_pieces()

        # Reset game variables
        for player in self.players:
            self.points[player] = 0
        self.last_move = {}


    def make_move(self, player, piece_x, piece_y, to_x, to_y):
        """Attempts to move the given piece"""
        # Check if move is legal
        piece_type = self.get_space(piece_x,piece_y)
        options = self.get_piece_options(player, piece_type, piece_x, piece_y)
        if (to_x, to_y) not in options:
            # Invalid move
            return False

        # Perform move action
        if self.get_space(to_x, to_y) == 0:
            # Move to empty space
            self.place(0, piece_x, piece_y)
            self.place(piece_type, to_x, to_y)
        elif not self.check_piece_ownership(player, to_x, to_y):
            # Take enemy piece
            self.points[player] += self.get_space(to_x, to_y) # Score points
            self.place(0, piece_x, piece_y)
            self.place(piece_type, to_x, to_y)
        elif self.can_field_promote(player, piece_x, piece_y, to_x, to_y):
            # Field promote
            promote_to = self.can_field_promote(player, piece_x, piece_y, to_x, to_y)
            self.place(0, piece_x, piece_y)
            self.place(promote_to, to_x, to_y)
        else:
            raise Exception("No action handler for move.")
        
        # Update last move
        crosses_canal = not self.check_piece_ownership(player, to_x, to_y)
        self.last_move = {"player": player, "from_x": piece_x, "from_y": piece_y, "to_x": to_x, "to_y": to_y, "crosses": crosses_canal}
        return True
