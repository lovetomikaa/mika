# -*- coding: utf-8 -*-
"""
🐾 Terminal Pet - 终端电子宠物
一只会吃、会睡、会玩的小精灵！
"""
import os
import sys
import time
import random
import json
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SAVE_FILE = Path.home() / '.terminal_pet.json'

# ASCII art for different states
PETS = {
    'happy': [
        r'   /\_/\  ',
        r'  ( o.o ) ',
        r'   > ^ <  ',
        r'  /|   |\ ',
        r' (_|   |_)',
    ],
    'neutral': [
        r'   /\_/\  ',
        r'  ( -.- ) ',
        r'   > ^ <  ',
        r'  /|   |\ ',
        r' (_|   |_)',
    ],
    'sad': [
        r'   /\_/\  ',
        r'  ( T_T ) ',
        r'   > ^ <  ',
        r'  /|   |\ ',
        r' (_|   |_)',
    ],
    'sleeping': [
        r'   /\_/\  ',
        r'  ( -.- ) ',
        r'   > ^ <  ',
        r'  /|   |\ ',
        r' (_|   |_) zzZ',
    ],
    'eating': [
        r'   /\_/\  ',
        r'  ( ^.^ ) ',
        r'   > o <  ',
        r'  /|   |\ ',
        r' (_|   |_)',
    ],
    'dead': [
        r'   /\_/\  ',
        r'  ( x.x ) ',
        r'   > ^ <  ',
        r'  /|   |\ ',
        r' (_|   |_) R.I.P',
    ],
}

EVOLUTIONS = {
    0: '小蛋蛋',
    1: '小精灵',
    2: '大精灵',
    3: '精灵王',
}

ITEMS = {
    '面包': {'hunger': 15, 'happiness': 2, 'price': 0},
    '蛋糕': {'hunger': 25, 'happiness': 10, 'price': 5},
    '鱼': {'hunger': 40, 'happiness': 15, 'price': 10},
    '披萨': {'hunger': 50, 'happiness': 25, 'price': 20},
    '神秘果实': {'hunger': 10, 'happiness': 50, 'price': 50},
}

GAMES = {
    '猜拳': 'rock_paper_scissors',
    '猜数字': 'guess_number',
    '投骰子': 'dice_roll',
}


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def print_pet(pet, state='neutral'):
    """Print the pet with current state"""
    art = PETS.get(state, PETS['neutral'])
    print()
    for line in art:
        print(f'    {line}')
    print()


def draw_bar(label, value, max_val=100, width=20):
    """Draw a progress bar"""
    filled = int(width * value / max_val)
    bar = '█' * filled + '░' * (width - filled)
    color = '🟢' if value > 60 else '🟡' if value > 30 else '🔴'
    print(f'  {color} {label}: [{bar}] {value}/{max_val}')


def save_pet(pet):
    """Save pet data to file"""
    with open(SAVE_FILE, 'w', encoding='utf-8') as f:
        json.dump(pet, f, ensure_ascii=False, indent=2)


def load_pet():
    """Load pet data from file"""
    if SAVE_FILE.exists():
        with open(SAVE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def new_pet():
    """Create a new pet"""
    name = input('  给你的宠物取个名字吧: ').strip() or '小精灵'
    return {
        'name': name,
        'hunger': 80,
        'happiness': 80,
        'energy': 100,
        'coins': 50,
        'level': 0,
        'exp': 0,
        'age': 0,
        'last_seen': time.time(),
        'alive': True,
    }


def update_pet(pet):
    """Update pet stats based on time passed"""
    if not pet['alive']:
        return
    
    now = time.time()
    hours_passed = (now - pet['last_seen']) / 3600
    
    # Stats decrease over time (but capped)
    pet['hunger'] = max(0, pet['hunger'] - int(hours_passed * 5))
    pet['happiness'] = max(0, pet['happiness'] - int(hours_passed * 3))
    pet['energy'] = min(100, pet['energy'] + int(hours_passed * 10))  # Recover energy
    pet['age'] += hours_passed / 24  # Age in days
    
    pet['last_seen'] = now
    
    # Check if pet died
    if pet['hunger'] <= 0 and pet['happiness'] <= 0:
        pet['alive'] = False
    
    # Check evolution
    if pet['level'] < 3 and pet['age'] >= (pet['level'] + 1) * 3:
        pet['level'] += 1
        print(f'  🎉 {pet["name"]} 进化成了 {EVOLUTIONS[pet["level"]]}！')


def get_state(pet):
    """Get current visual state of pet"""
    if not pet['alive']:
        return 'dead'
    if pet['happiness'] > 70:
        return 'happy'
    if pet['happiness'] < 30:
        return 'sad'
    return 'neutral'


def play_game(pet):
    """Play a mini-game to earn coins and happiness"""
    print('\n  🎮 选择游戏:')
    games = list(GAMES.keys())
    for i, g in enumerate(games, 1):
        print(f'    {i}. {g}')
    print(f'    0. 返回')
    
    choice = input('  选择: ').strip()
    
    if choice == '1':  # Rock Paper Scissors
        print('\n  ✊ 石头剪刀布！')
        print('    1. 石头  2. 剪刀  3. 布')
        player = input('    你出: ').strip()
        computer = random.choice(['1', '2', '3'])
        names = {'1': '石头', '2': '剪刀', '3': '布'}
        
        print(f'    你出了 {names.get(player, "?")}, 宠物出了 {names[computer]}')
        
        wins = [('1','2'), ('2','3'), ('3','1')]
        if (player, computer) in wins:
            print('    🎉 你赢了！+10金币 +15开心')
            pet['coins'] += 10
            pet['happiness'] = min(100, pet['happiness'] + 15)
        elif player == computer:
            print('    🤝 平局！+5金币 +5开心')
            pet['coins'] += 5
            pet['happiness'] = min(100, pet['happiness'] + 5)
        else:
            print('    😅 你输了！+2金币 +2开心')
            pet['coins'] += 2
            pet['happiness'] = min(100, pet['happiness'] + 2)
        
    elif choice == '2':  # Guess Number
        print('\n  🔢 猜数字！(1-10)')
        target = random.randint(1, 10)
        guess = input('    你猜: ').strip()
        
        if guess.isdigit() and int(guess) == target:
            print(f'    🎉 猜对了！答案是 {target}！+20金币 +20开心')
            pet['coins'] += 20
            pet['happiness'] = min(100, pet['happiness'] + 20)
        else:
            print(f'    😅 答案是 {target}，你猜错了！+5金币 +3开心')
            pet['coins'] += 5
            pet['happiness'] = min(100, pet['happiness'] + 3)
            
    elif choice == '3':  # Dice Roll
        print('\n  🎲 投骰子比大小！')
        player = random.randint(1, 6)
        computer = random.randint(1, 6)
        print(f'    你投了 {player}，宠物投了 {computer}')
        
        if player > computer:
            print('    🎉 你赢了！+15金币 +10开心')
            pet['coins'] += 15
            pet['happiness'] = min(100, pet['happiness'] + 10)
        elif player < computer:
            print('    😅 你输了！+3金币 +3开心')
            pet['coins'] += 3
            pet['happiness'] = min(100, pet['happiness'] + 3)
        else:
            print('    🤝 平局！+8金币 +5开心')
            pet['coins'] += 8
            pet['happiness'] = min(100, pet['happiness'] + 5)


def feed_pet(pet):
    """Feed the pet"""
    print('\n  🍽️ 选择食物:')
    items = list(ITEMS.items())
    for i, (name, data) in enumerate(items, 1):
        emoji = ['🍞', '🍰', '🐟', '🍕', '🍇'][i-1]
        print(f'    {i}. {emoji} {name} (+{data["hunger"]}饱食 +{data["happiness"]}开心) - {data["price"]}金币')
    print(f'    0. 返回')
    
    choice = input('  选择: ').strip()
    if choice.isdigit() and 1 <= int(choice) <= len(items):
        name, data = items[int(choice) - 1]
        if pet['coins'] >= data['price']:
            pet['coins'] -= data['price']
            pet['hunger'] = min(100, pet['hunger'] + data['hunger'])
            pet['happiness'] = min(100, pet['happiness'] + data['happiness'])
            print(f'    🎉 {pet["name"]} 吃了 {name}，很满足！')
            print_pet(pet, 'eating')
        else:
            print(f'    💰 金币不够！需要 {data["price"]}，你只有 {pet["coins"]}')


def sleep_pet(pet):
    """Let the pet sleep"""
    print('\n  😴 宠物正在睡觉...')
    print_pet(pet, 'sleeping')
    for i in range(3):
        print('    z z Z', end='', flush=True)
        time.sleep(1)
    print()
    pet['energy'] = 100
    pet['happiness'] = min(100, pet['happiness'] + 10)
    print(f'    🌟 {pet["name"]} 睡醒了，精力充沛！')


def main():
    clear_screen()
    
    print()
    print('  ╔══════════════════════════════════╗')
    print('  ║    🐾 终端电子宠物 v1.0 🐾      ║')
    print('  ╚══════════════════════════════════╝')
    print()
    
    # Try to load existing pet
    pet = load_pet()
    
    if pet:
        update_pet(pet)
        print(f'  👋 {pet["name"]} 回来了！')
        if not pet['alive']:
            print(f'  💔 {pet["name"]} 已经... 去彩虹桥了...')
            print(f'  🌈 它陪伴了你 {pet["age"]:.1f} 天')
            choice = input('  要养一只新的吗？(y/n): ').strip().lower()
            if choice == 'y':
                pet = new_pet()
            else:
                print('  谢谢你的陪伴，再见！')
                return
    else:
        print('  🥚 你获得了一颗蛋！')
        pet = new_pet()
        save_pet(pet)
        print(f'  🎉 {pet["name"]} 诞生了！')
    
    while pet['alive']:
        clear_screen()
        state = get_state(pet)
        
        print(f'  ╔══════════════════════════════════╗')
        print(f'  ║  🐾 {pet["name"]} ({EVOLUTIONS[pet["level"]]})  Lv.{pet["level"]}  ║')
        print(f'  ╚══════════════════════════════════╝')
        
        print_pet(pet, state)
        draw_bar('饱食', pet['hunger'])
        draw_bar('开心', pet['happiness'])
        draw_bar('精力', pet['energy'])
        print(f'  💰 金币: {pet["coins"]}  📅 年龄: {pet["age"]:.1f}天')
        print()
        print('  1. 🍽️ 喂食  2. 🎮 玩耍  3. 😴 睡觉  4. 📊 状态  0. 退出')
        
        choice = input('  选择: ').strip()
        
        if choice == '1':
            feed_pet(pet)
        elif choice == '2':
            if pet['energy'] >= 20:
                play_game(pet)
                pet['energy'] -= 20
            else:
                print('    😴 宠物太累了，让它睡一觉吧！')
        elif choice == '3':
            sleep_pet(pet)
        elif choice == '4':
            print(f'\n  📊 {pet["name"]} 的详细状态:')
            print(f'    名字: {pet["name"]}')
            print(f'    形态: {EVOLUTIONS[pet["level"]]}')
            print(f'    年龄: {pet["age"]:.1f} 天')
            print(f'    等级: Lv.{pet["level"]}')
            print(f'    金币: {pet["coins"]}')
            print(f'    状态: {"开心" if state == "happy" else "普通" if state == "neutral" else "难过"}')
        elif choice == '0':
            save_pet(pet)
            print(f'  👋 {pet["name"]} 会想你的！')
            break
        
        save_pet(pet)
        input('\n  按回车继续...')
    
    if not pet['alive']:
        clear_screen()
        print('\n  💔 你的宠物离开了...')
        print_pet(pet, 'dead')
        print(f'  🌈 {pet["name"]} 陪伴了你 {pet["age"]:.1f} 天')
        print(f'  最高等级: {EVOLUTIONS[pet["level"]]}')
        save_file = SAVE_FILE
        save_file.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
