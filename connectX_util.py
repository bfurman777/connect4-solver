from linecache import cache
from tabnanny import check
import numpy as np
import multiprocessing as mp
import time

# ---------------------------------------- #
BRIAN, SASHA = 'G', 'B'
FIRST_PLAYER = SASHA
# ---------------------------------------- #

WIDTH, HEIGHT = 7,6  # dimentions (7x6 standard)
EMPTY = '*'
CONNECT_X = 4
MAX_DEPTH = 9  # starting depth that increases over time - 9 on standard board
LOG_FILENAME = 'log.txt'

CONNECT_X_VALUE = 1000  # score for a win, multiplied by the layers left in the search
CONNECT_X_CLOSE_VALUE = 0 #69  # score added for a setup for winning (aka 3 in a row)
MAX_NEG_SCORE = -9999999  # represents an illegal move that should never be chosen

TIME_DIFF_INC_DEPTH = 3.1  # if the time if less that this (sec), increament MAX_DEPTH


'''
Print to console and logfile
'''
def printLog(*args, **kwargs):
    print(*args, **kwargs)
    with open(LOG_FILENAME,'a') as file:
        print(*args, **kwargs, file=file)

def print_board(board):
    printLog(board)
    printLog()
    printLog(np.array([[str(i) for i in range(0,WIDTH)]]), '(columns)')
    printLog()

def empty_board():
    return np.full((HEIGHT,WIDTH), EMPTY) 

'''
Check if a cord is on the board
@param cords: (r,c) tuple of just placed move
@return: True if valid, False if out of bounds
'''
def valid_cord(cords):
    r,c = cords
    return not (r < 0 or c < 0 or r >= HEIGHT or c >= WIDTH)

'''
Updates the board with a move, if it is valid
@param move: colm index of move
@param player: player value
return: (r,c) move cordinates on success, None on invalid move
'''
def place_move(move, player, board):
    c = move
    if not valid_cord((0,c)):  # does colm exist?
        return None
    colm = board[:,c]
    for r in range(len(colm)):
        if colm[r] != EMPTY:
            if r == 0:  # full colm, illegal move
                return None
            else:
                r = r - 1
                break  # we found the bottom piece
    board[r,c] = player
    return r,c

'''
Remove the top of a colm (assuming move already placed)
@param move: colm index of previously placed move
'''
def remove_move(move, board):
    c = move
    colm = board[:,c]
    for r in range(HEIGHT):
        if colm[r] != EMPTY:
            colm[r] = EMPTY
            return

def next_player(cur_player):
    return SASHA if cur_player is BRIAN else BRIAN

'''
Check a win of a move (assuming move already placed)
@param cords: (r,c) tuple of just placed move
@param to_win: number in a row needed to win
@return True on win, False otherwise
'''
def check_win(cords, board, to_win=CONNECT_X):
    rN, cN = cords  # new chip cords
    player = board[rN,cN]
    count = 1  # how many in a row so far
    if player is EMPTY:
        return False
    
    # check vertical with sliding windows
    count = 1
    # grow upwards
    for r in range(rN - 1, -1, -1):
        if board[r,cN] != player:
            break
        count += 1
    # grow downwards
    for r in range(rN + 1, HEIGHT, 1):
        if board[r,cN] != player:
            break
        count += 1
    # check win
    if count >= to_win:
        return True

    # check horizontal with sliding windows
    count = 1
    # grow leftwards
    for c in range(cN - 1, -1, -1):
        if board[rN,c] != player:
            break
        count += 1
    # grow rightwards
    for c in range(cN + 1, WIDTH, 1):
        if board[rN,c] != player:
            break
        count += 1
    # check win
    if count >= to_win:
        return True
    
    # check top-left to bottom-right with sliding windows
    count = 1
    # grow up-left
    r, c = rN - 1, cN - 1
    while True:
        if not valid_cord((r,c)) or board[r,c] != player:
            break
        r, c = r - 1, c - 1
        count += 1
    # grow down-right
    r, c = rN + 1, cN + 1
    while True:
        if not valid_cord((r,c)) or board[r,c] != player:
            break
        r, c = r + 1, c + 1
        count += 1
    # check win
    if count >= to_win:
        return True

    # check top-right to bottom-left with sliding windows
    count = 1
    # grow up-right
    r, c = rN - 1, cN + 1
    while True:
        if not valid_cord((r,c)) or board[r,c] != player:
            break
        r, c = r - 1, c + 1
        count += 1
    # grow down-left
    r, c = rN + 1, cN - 1
    while True:
        if not valid_cord((r,c)) or board[r,c] != player:
            break
        r, c = r + 1, c - 1
        count += 1
    # check win
    if count >= to_win:
        return True

    return False

'''
@return a hashable key value for the current board.
'''
def encode_board(board):
    return board.tobytes()

'''
@return new numpy array from the encoded board
'''
def reconstruct_board(encoded_board):
    return np.frombuffer(encoded_board, dtype=board.dtype).reshape(board.shape)

'''
def eval_score(cord, depth, player)
    win:        return 1000
    max_depth:  return 0
    connectX-1: return 50 + (n/a)
    n/a:        return max([-recurse(m, depth+1, next_player) for m in moves])

@param cords: cords of previous turn
@param player: player of previous turn
@param layer: current layers of depth remaining
@param cache: dict of {board_hash:score}
@return: value of that previous turn's move
'''
def eval_score(cords, player, layer, cache, board):
    h = encode_board(board)
    if h in cache:
        return cache[h]

    ret_val = MAX_NEG_SCORE
    if check_win(cords, board):
        ret_val = CONNECT_X_VALUE * (1 + (layer / MAX_DEPTH))  # extra value if you win sooner
    elif layer == 0:
        ret_val = 0  # too deep
    else:
        connectx_close_score = CONNECT_X_CLOSE_VALUE if CONNECT_X_CLOSE_VALUE and check_win(cords, board, CONNECT_X-1) else 0
        scores = [None for i in range(WIDTH)]
        next_p = next_player(player)
        for c in range(WIDTH):
            # make a move, store it on stack, recurse, undo move - all on the same board
            cords = place_move(c, next_p, board)
            if cords is None:
                continue
            scores[c] = eval_score(cords, next_p, layer-1, cache, board)
            remove_move(c, board)
        scores = [s for s in scores if s != None]  # remove illegal moves
        if len(scores) == 0:
            ret_val = MAX_NEG_SCORE
        else:
            enemy_score = max(scores)  # calculate max, assuming they do best move every time
            ret_val = -enemy_score + connectx_close_score
    
    cache[h] = ret_val
    return ret_val


def eval_score_proc_wrapper(cords, player, layer, cache, scores, board):
    c = cords[1]
    scores[c] = eval_score(cords, player, layer, cache, board)
    return 0

'''
Single thread to find best move 
return: (the best move, list of move scores)
'''
def best_move_lite(player, board, depth=2):
    start_time = time.time()

    scores = [MAX_NEG_SCORE for i in range(WIDTH)]
    cache = dict() #manager.dict()

    for c in range(WIDTH):
        cords = place_move(c, player, board)
        if cords is None:
            continue
        
        eval_score_proc_wrapper(cords, player, depth, cache, scores, board)

        remove_move(c, board)

    # sketchy fix to get the most "middle" move
    max_score = max(scores)
    best_scores = [i for i,s in enumerate(scores) if s == max_score]
    
    del cache
    move = min(best_scores, key=lambda x:abs(x - (WIDTH // 2)))

    return move, scores

'''
Uses multiprocessing to find best move
return: (the best move, list of move scores)
'''
def best_move(player, board):
    start_time = time.time()

    global MAX_DEPTH
    procs = []
    manager = mp.Manager()
    scores = manager.list([MAX_NEG_SCORE for i in range(WIDTH)])
    cache = dict() #manager.dict()

    for c in range(WIDTH):
        cords = place_move(c, player, board)
        if cords is None:
            continue
        
        p = mp.Process(target=eval_score_proc_wrapper, 
            args=(cords, player, MAX_DEPTH, cache, scores, board))
        procs.append(p)
        p.start()
        
        remove_move(c, board)

    for p in procs:
        p.join()

    # sketchy fix to get the most "middle" move
    max_score = max(scores)
    best_scores = [i for i,s in enumerate(scores) if s == max_score]
    
    del cache
    diff_time = int((time.time() - start_time) * 100) / 100.0  # 100th second
    move = min(best_scores, key=lambda x:abs(x - (WIDTH // 2)))
    printLog(f'Calculated best move of ({move}):   time={diff_time}s   depth={MAX_DEPTH}\n')

    if diff_time < TIME_DIFF_INC_DEPTH:
        MAX_DEPTH += 1
        printLog("maximum depth has increased..\n")

    return move, scores
