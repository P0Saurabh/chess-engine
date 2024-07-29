import google.generativeai as genai
import logging
import sys
import time

# Configure logging to print to console
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Configure the Gemini API with the API key directly
genai.configure(api_key="AIzaSyCDhu6BQo9XrD_qcCV5fwpeMa0aIA7OlpQ")

# Generation configuration for the Gemini model
generation_config = {
    "temperature": 1,
    "top_p": 1,
    "top_k": 1,
    "max_output_tokens": 2048,
}

# Initialize the model
model = genai.GenerativeModel(
    model_name="gemini-1.0-pro",
    generation_config=generation_config,
)


def get_next_move_from_gemini(fen):
    try:
        chat_session = model.start_chat(
            history=[
                {
                    "role": "user",
                    "parts": [
                        f"Give me the next move for this FEN string: {fen}\n",
                    ],
                },
            ]
        )
        response = chat_session.send_message(f"Give me the next move for this FEN string: {fen}")
        move = response.text.strip()
        logging.debug(f"Next move from Gemini: {move}")
        return move
    except Exception as e:
        logging.error(f"Error getting move from Gemini: {e}")
        return None


class ChessEngine:
    def __init__(self):
        self.board = self.initialize_board()
        self.current_turn = 'white'  # Start with white
        self.move_history = []
        self.nodes_evaluated = 0
        self.start_time = time.time()
        self.hash_table = {}  # Placeholder for hash table

    def initialize_board(self):
        return [
            ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r'],
            ['p', 'p', 'p', 'p', 'p', 'p', 'p', 'p'],
            ['.', '.', '.', '.', '.', '.', '.', '.'],
            ['.', '.', '.', '.', '.', '.', '.', '.'],
            ['.', '.', '.', '.', '.', '.', '.', '.'],
            ['.', '.', '.', '.', '.', '.', '.', '.'],
            ['P', 'P', 'P', 'P', 'P', 'P', 'P', 'P'],
            ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R']
        ]

    def board_to_fen(self):
        fen = ''
        for row in self.board:
            empty_count = 0
            for cell in row:
                if cell == '.':
                    empty_count += 1
                else:
                    if empty_count > 0:
                        fen += str(empty_count)
                        empty_count = 0
                    fen += cell
            if empty_count > 0:
                fen += str(empty_count)
            fen += '/'
        fen = fen[:-1]  # Remove the last '/'
        fen += ' w' if self.current_turn == 'white' else ' b'
        fen += ' KQkq - 0 1'  # Simplified for now
        return fen

    def parse_fen(self, fen_string):
        try:
            parts = fen_string.split()
            board_fen = parts[0]
            turn = parts[1]

            rows = board_fen.split('/')
            self.board = []
            for row in rows:
                parsed_row = []
                for char in row:
                    if char.isdigit():
                        parsed_row.extend(['.'] * int(char))
                    else:
                        parsed_row.append(char)
                self.board.append(parsed_row)

            self.current_turn = 'black' if turn == 'b' else 'white'
        except Exception as e:
            logging.error(f"Error parsing FEN: {e}")

    def get_next_move(self):
        fen = self.board_to_fen()
        logging.debug(f"FEN: {fen}")
        move = get_next_move_from_gemini(fen)
        if move is None:
            move = "e2e4"  # Fallback move
            logging.warning("Using fallback move: e2e4")
        return move

    def handle_uci_commands(self):
        input = sys.stdin
        output = sys.stdout
        while True:
            command = input.readline().strip()
            logging.debug(f"Received command: {command}")

            if command == "uci":
                self.send_uci_info(output)
            elif command == "isready":
                output.write("readyok\n")
                output.flush()
            elif command.startswith("position"):
                self.set_position(command)
            elif command.startswith("go"):
                if self.current_turn == 'black':
                    start_time = time.time()
                    move = self.get_next_move()
                    end_time = time.time()

                    self.nodes_evaluated += 1  # Increment nodes evaluated (Placeholder)

                    nps = self.nodes_evaluated / (end_time - start_time)  # Nodes per second calculation
                    hash_usage = len(self.hash_table)  # Hash table usage (Placeholder)

                    output.write(f"bestmove {move}\n")
                    output.write(f"info string Current move: {move}\n")
                    output.write(f"info string Nodes evaluated: {self.nodes_evaluated}\n")
                    output.write(f"info string Nodes per second: {nps:.2f}\n")
                    output.write(f"info string Hash table usage: {hash_usage}\n")
                    output.flush()
                else:
                    logging.debug("It's white's turn. Waiting for the user to move.")
            elif command.startswith("setboard"):
                self.set_board_from_fen(command.split(maxsplit=1)[1])
            elif command == "quit":
                break

    def send_uci_info(self, output):
        output.write("id name MyChessEngine\n")
        output.write("id author YourName\n")
        output.write("uciok\n")
        output.flush()

    def set_position(self, command):
        parts = command.split()
        if parts[1] == "startpos":
            self.board = self.initialize_board()
            self.current_turn = 'white'
            if len(parts) > 2 and parts[2] == "moves":
                moves = parts[3:]
                for move in moves:
                    self.make_uci_move(move)
        elif parts[1] == "fen":
            fen_string = " ".join(parts[2:])
            self.parse_fen(fen_string)

    def set_board_from_fen(self, fen_string):
        logging.debug(f"Setting board from FEN: {fen_string}")
        self.parse_fen(fen_string)

    def make_uci_move(self, move):
        move = move.strip()
        if len(move) != 4:
            logging.error(f"Invalid move format: {move}")
            return

        from_square = (8 - int(move[1]), ord(move[0]) - ord('a'))
        to_square = (8 - int(move[3]), ord(move[2]) - ord('a'))

        if not (0 <= from_square[0] < 8 and 0 <= from_square[1] < 8 and
                0 <= to_square[0] < 8 and 0 <= to_square[1] < 8):
            logging.error(f"Invalid move coordinates: from {from_square} to {to_square}")
            return

        self.board[to_square[0]][to_square[1]] = self.board[from_square[0]][from_square[1]]
        self.board[from_square[0]][from_square[1]] = '.'
        logging.debug(f"Updated board: {self.board}")

    def is_game_over(self):
        # Implement game over logic, e.g., check for checkmate or stalemate
        return False


if __name__ == "__main__":
    engine = ChessEngine()
    engine.handle_uci_commands()
