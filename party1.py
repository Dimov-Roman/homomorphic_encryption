import csv
import random
import pickle
import os
import torch
import torch.distributed as dist
import config
from phe import paillier

NUM_TRIPLES = 10  # Количество троек для генерации


def init_distributed():
    """Инициализация torch.distributed с использованием переменных окружения"""
    master_addr = os.environ.get('MASTER_ADDR', 'localhost')
    master_port = os.environ.get('MASTER_PORT', '29500')
    
    os.environ['MASTER_ADDR'] = master_addr
    os.environ['MASTER_PORT'] = master_port
    
    dist.init_process_group(
        backend='gloo',
        rank=0,
        world_size=2,
        init_method=f'tcp://{master_addr}:{master_port}'
    )


def generate_triples():
    """
    Сторона 1: Генерирует ключи Paillier и координирует генерацию троек
    
    Протокол генерации троек Бивера без TTP:
    1. Сторона 1 генерирует пару ключей Paillier (pk, sk)
    2. Сторона 1 отправляет pk стороне 2
    3. Для каждой тройки:
       a. Сторона 1 выбирает случайные a1, b1
       b. Сторона 2 выбирает случайные a2, b2
       c. Сторона 1 отправляет Enc(a1), Enc(b1) стороне 2
       d. Сторона 2 вычисляет Enc(a1*b2 + a2*b1 + a2*b2) и отправляет стороне 1
       e. Сторона 1 расшифровывает и вычисляет c1 = a1*b1 + Dec(...)
       f. Сторона 2 вычисляет c2 = a2*b2
       g. Результат: (a1, b1, c1) для стороны 1, (a2, b2, c2) для стороны 2
       h. Свойство: (a1+a2) * (b1+b2) = c1+c2 (mod MPC_MODULO)
    """
    # Инициализация distributed
    init_distributed()
    
    print("Party 1: Generating Paillier keypair...")
    public_key, private_key = paillier.generate_paillier_keypair(n_length=config.PAILLIER_KEY_SIZE)
    
    # Отправляем публичный ключ стороне 2
    print("Party 1: Sending public key to Party 2...")
    pk_data = pickle.dumps(public_key)
    pk_size_tensor = torch.tensor([len(pk_data)], dtype=torch.long)
    dist.send(pk_size_tensor, dst=1)
    
    # Конвертируем в tensor для отправки
    pk_tensor = torch.ByteTensor(list(pk_data))
    dist.send(pk_tensor, dst=1)
    
    triples_p1 = []
    
    for i in range(NUM_TRIPLES):
        print(f"Party 1: Generating triple {i+1}/{NUM_TRIPLES}...")
        
        # Выбираем случайные a1 и b1
        a1 = random.randint(0, config.MPC_MODULO - 1)
        b1 = random.randint(0, config.MPC_MODULO - 1)
        
        # Шифруем a1 и b1
        enc_a1 = public_key.encrypt(a1)
        enc_b1 = public_key.encrypt(b1)
        
        # Отправляем зашифрованные значения стороне 2
        enc_a1_data = pickle.dumps(enc_a1)
        enc_b1_data = pickle.dumps(enc_b1)
        
        # Отправляем enc_a1
        size_tensor = torch.tensor([len(enc_a1_data)], dtype=torch.long)
        dist.send(size_tensor, dst=1)
        data_tensor = torch.ByteTensor(list(enc_a1_data))
        dist.send(data_tensor, dst=1)
        
        # Отправляем enc_b1
        size_tensor = torch.tensor([len(enc_b1_data)], dtype=torch.long)
        dist.send(size_tensor, dst=1)
        data_tensor = torch.ByteTensor(list(enc_b1_data))
        dist.send(data_tensor, dst=1)
        
        # Получаем зашифрованное значение от стороны 2: Enc(a1*b2 + a2*b1 + a2*b2)
        size_tensor = torch.tensor([0], dtype=torch.long)
        dist.recv(size_tensor, src=1)
        
        data_tensor = torch.ByteTensor(size_tensor.item())
        dist.recv(data_tensor, src=1)
        
        enc_value = pickle.loads(bytes(data_tensor.tolist()))
        
        # Расшифровываем: s = a1*b2 + a2*b1 + a2*b2
        s = private_key.decrypt(enc_value)
        
        # Вычисляем c1 = a1*b1 + s (mod MPC_MODULO)
        # Теперь: c1 + c2 = a1*b1 + a1*b2 + a2*b1 + a2*b2 + a2*b2 - a2*b2
        #               = a1*b1 + a1*b2 + a2*b1 + a2*b2
        #               = (a1 + a2) * (b1 + b2)
        c1 = (a1 * b1 + s) % config.MPC_MODULO
        
        triples_p1.append((a1, b1, c1))
    
    # Сохраняем в CSV
    print("Party 1: Saving triples to p1.csv...")
    with open('/shared/p1.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['a', 'b', 'c'])
        for triple in triples_p1:
            writer.writerow(triple)
    
    print("Party 1: Done!")
    print(f"Party 1: Generated {len(triples_p1)} triples")
    print("Party 1: First triple:", triples_p1[0] if triples_p1 else "None")
    
    dist.destroy_process_group()


if __name__ == '__main__':
    generate_triples()
