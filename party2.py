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
        rank=1,
        world_size=2,
        init_method=f'tcp://{master_addr}:{master_port}'
    )


def generate_triples():
    """
    Сторона 2: Получает публичный ключ и участвует в генерации троек
    
    Протокол:
    1. Получает публичный ключ pk от стороны 1
    2. Для каждой тройки:
       a. Выбирает случайные a2, b2
       b. Получает Enc(a1), Enc(b1) от стороны 1
       c. Используя гомоморфные свойства Paillier, вычисляет:
          Enc(a1*b2 + a2*b1 + a2*b2) = Enc(a1)*b2 + Enc(b1)*a2 + Enc(a2*b2)
       d. Отправляет результат стороне 1
       e. Сохраняет c2 = a2*b2
    """
    # Инициализация distributed
    init_distributed()
    
    print("Party 2: Waiting for public key from Party 1...")
    
    # Получаем публичный ключ от стороны 1
    pk_size_tensor = torch.tensor([0], dtype=torch.long)
    dist.recv(pk_size_tensor, src=0)
    
    pk_tensor = torch.ByteTensor(pk_size_tensor.item())
    dist.recv(pk_tensor, src=0)
    
    public_key = pickle.loads(bytes(pk_tensor.tolist()))
    print("Party 2: Received public key")
    
    triples_p2 = []
    
    for i in range(NUM_TRIPLES):
        print(f"Party 2: Generating triple {i+1}/{NUM_TRIPLES}...")
        
        # Выбираем случайные a2 и b2
        a2 = random.randint(0, config.MPC_MODULO - 1)
        b2 = random.randint(0, config.MPC_MODULO - 1)
        
        # Получаем enc(a1) и enc(b1) от стороны 1
        # Получаем enc_a1
        size_tensor = torch.tensor([0], dtype=torch.long)
        dist.recv(size_tensor, src=0)
        data_tensor = torch.ByteTensor(size_tensor.item())
        dist.recv(data_tensor, src=0)
        enc_a1 = pickle.loads(bytes(data_tensor.tolist()))
        
        # Получаем enc_b1
        size_tensor = torch.tensor([0], dtype=torch.long)
        dist.recv(size_tensor, src=0)
        data_tensor = torch.ByteTensor(size_tensor.item())
        dist.recv(data_tensor, src=0)
        enc_b1 = pickle.loads(bytes(data_tensor.tolist()))
        
        # Используем гомоморфные свойства Paillier:
        # Enc(m1 + m2) = Enc(m1) * Enc(m2)
        # Enc(k * m) = Enc(m)^k
        
        # Вычисляем Enc(a1*b2 + a2*b1 + a2*b2):
        
        # 1. Enc(a1 * b2) = Enc(a1)^b2 (в библиотеке phe это enc_a1 * b2)
        enc_a1_b2 = enc_a1 * b2
        
        # 2. Enc(b1 * a2) = Enc(b1)^a2 (в библиотеке phe это enc_b1 * a2)
        enc_b1_a2 = enc_b1 * a2
        
        # 3. Enc(a2 * b2) - шифруем явно
        enc_a2_b2 = public_key.encrypt((a2 * b2) % config.MPC_MODULO)
        
        # 4. Enc(a1*b2 + a2*b1 + a2*b2) = Enc(a1*b2) * Enc(a2*b1) * Enc(a2*b2)
        enc_sum = enc_a1_b2 + enc_b1_a2 + enc_a2_b2
        
        # Отправляем результат стороне 1
        enc_sum_data = pickle.dumps(enc_sum)
        size_tensor = torch.tensor([len(enc_sum_data)], dtype=torch.long)
        dist.send(size_tensor, dst=0)
        data_tensor = torch.ByteTensor(list(enc_sum_data))
        dist.send(data_tensor, dst=0)
        
        # Сохраняем c2 = a2 * b2 (mod MPC_MODULO)
        c2 = (a2 * b2) % config.MPC_MODULO
        
        triples_p2.append((a2, b2, c2))
    
    # Сохраняем в CSV
    print("Party 2: Saving triples to p2.csv...")
    with open('/shared/p2.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['a', 'b', 'c'])
        for triple in triples_p2:
            writer.writerow(triple)
    
    print("Party 2: Done!")
    print(f"Party 2: Generated {len(triples_p2)} triples")
    print("Party 2: First triple:", triples_p2[0] if triples_p2 else "None")
    
    dist.destroy_process_group()


if __name__ == '__main__':
    generate_triples()
