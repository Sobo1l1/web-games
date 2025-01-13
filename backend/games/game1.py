from fastapi import APIRouter, WebSocket
from pydantic import BaseModel
from typing import List, Tuple, Optional
import json
import asyncio

router = APIRouter()

class Direction(BaseModel):
    direction: str

class GameState(BaseModel):
    snake: List[List[int]]
    food: List[int]
    score: int
    game_over: bool

class SnakeGame:
    def __init__(self):
        self.width = 20
        self.height = 20
        self.speed = 0.5  # Сделаем движение медленнее для отладки
        self.reset_game()

    def reset_game(self):
        self.snake = [(10, 10)]  # Start in middle
        self.direction = 'RIGHT'
        self.food = self.spawn_food()
        self.score = 0
        self.game_over = False

    def spawn_food(self):
        # Simple food spawning logic (to be improved)
        from random import randint
        x = randint(0, self.width - 1)
        y = randint(0, self.height - 1)
        return (x, y)

    def move(self, new_direction=None):
        if self.game_over:
            return False

        # Update direction if provided
        if new_direction:
            valid_moves = {
                'UP': {'UP', 'LEFT', 'RIGHT'},
                'DOWN': {'DOWN', 'LEFT', 'RIGHT'},
                'LEFT': {'UP', 'DOWN', 'LEFT'},
                'RIGHT': {'UP', 'DOWN', 'RIGHT'}
            }
            if new_direction in valid_moves[self.direction]:
                self.direction = new_direction

        # Move snake
        head = self.snake[0]
        if self.direction == 'UP':
            new_head = (head[0], head[1] - 1)
        elif self.direction == 'DOWN':
            new_head = (head[0], head[1] + 1)
        elif self.direction == 'LEFT':
            new_head = (head[0] - 1, head[1])
        else:  # RIGHT
            new_head = (head[0] + 1, head[1])

        # Check collisions
        if (new_head[0] < 0 or new_head[0] >= self.width or
            new_head[1] < 0 or new_head[1] >= self.height or
            new_head in self.snake):
            self.game_over = True
            return False

        self.snake.insert(0, new_head)
        
        # Check if food eaten
        if new_head == self.food:
            self.score += 1
            self.food = self.spawn_food()
        else:
            self.snake.pop()

        return True

    def get_state(self):
        # Преобразуем кортежи в списки для JSON
        snake_list = [[x, y] for x, y in self.snake]
        food_list = [self.food[0], self.food[1]]
        
        return {
            'snake': snake_list,
            'food': food_list,
            'score': self.score,
            'game_over': self.game_over
        }

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    game = SnakeGame()
    
    try:
        # Отправим начальное состояние
        await websocket.send_json(game.get_state())
        
        # Task for automatic movement
        async def auto_move():
            while not game.game_over:
                await asyncio.sleep(game.speed)
                game.move()
                state = game.get_state()
                await websocket.send_json(state)
                if game.game_over:
                    break
        
        # Start auto-move task
        auto_move_task = asyncio.create_task(auto_move())
        
        # Handle player input
        while not game.game_over:
            try:
                data = await websocket.receive_text()
                movement = Direction.parse_raw(data)
                game.move(movement.direction)
                await websocket.send_json(game.get_state())
            except Exception as e:
                print(f"Error handling input: {e}")
                break
                
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        if 'auto_move_task' in locals():
            auto_move_task.cancel()
        await websocket.close()

@router.post("/start")
async def start_game():
    game = SnakeGame()
    return game.get_state()
