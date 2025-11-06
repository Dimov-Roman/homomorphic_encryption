"""
Скрипт для проверки корректности сгенерированных троек Бивера.
Проверяет, что для каждой тройки (a1, b1, c1) и (a2, b2, c2):
(a1 + a2) * (b1 + b2) = c1 + c2 (mod MPC_MODULO)
"""

import csv
import config


def load_triples(filename):
    """Загрузка троек из CSV файла"""
    triples = []
    with open(filename, 'r') as f:
        reader = csv.reader(f)
        next(reader)  # Пропускаем заголовок
        for row in reader:
            triples.append(tuple(int(x) for x in row))
    return triples


def verify_triples(triples_p1, triples_p2):
    """
    Проверка корректности троек Бивера.
    Для каждой пары троек проверяем:
    (a1 + a2) * (b1 + b2) ≡ c1 + c2 (mod MPC_MODULO)
    """
    if len(triples_p1) != len(triples_p2):
        raise ValueError(f"Число троек не совпадает: {len(triples_p1)} vs {len(triples_p2)}")
    
    print(f"Проверка {len(triples_p1)} троек Бивера...")
    
    for i, ((a1, b1, c1), (a2, b2, c2)) in enumerate(zip(triples_p1, triples_p2)):
        # Вычисляем a = a1 + a2, b = b1 + b2
        a = (a1 + a2) % config.MPC_MODULO
        b = (b1 + b2) % config.MPC_MODULO
        c = (c1 + c2) % config.MPC_MODULO
        
        # Проверяем, что a * b = c (mod MPC_MODULO)
        expected = (a * b) % config.MPC_MODULO
        
        if expected != c:
            raise ValueError(
                f"Тройка {i+1} некорректна!\n"
                f"  a1={a1}, b1={b1}, c1={c1}\n"
                f"  a2={a2}, b2={b2}, c2={c2}\n"
                f"  a={a}, b={b}\n"
                f"  Ожидалось: a*b = {expected}\n"
                f"  Получено: c = {c}"
            )
        
        print(f"  Тройка {i+1}: ✓ ({a} * {b} = {c} mod {config.MPC_MODULO})")
    
    print("\n✓ Все тройки корректны!")
    return True


def main():
    print("=" * 60)
    print("Проверка мультипликативных троек Бивера")
    print("=" * 60)
    
    print("\nЗагрузка троек из файлов...")
    triples_p1 = load_triples('p1.csv')
    triples_p2 = load_triples('p2.csv')
    
    print(f"Загружено {len(triples_p1)} троек от стороны 1")
    print(f"Загружено {len(triples_p2)} троек от стороны 2")
    
    print(f"\nПараметры:")
    print(f"  PAILLIER_KEY_SIZE: {config.PAILLIER_KEY_SIZE}")
    print(f"  MPC_MODULO: {config.MPC_MODULO}")
    
    verify_triples(triples_p1, triples_p2)
    
    print("\n" + "=" * 60)
    print("MPC-умножение с использованием троек Бивера")
    print("=" * 60)
    
    # Демонстрация использования троек для MPC-умножения
    # Предположим, сторона 1 имеет x1, сторона 2 имеет x2
    # Они хотят вычислить (x1 + x2) * (y1 + y2) без раскрытия своих значений
    
    x1, y1 = 42, 17
    x2, y2 = 13, 28
    
    print(f"\nПример: сторона 1 имеет x1={x1}, y1={y1}")
    print(f"         сторона 2 имеет x2={x2}, y2={y2}")
    print(f"         Цель: вычислить (x1+x2) * (y1+y2) = {(x1+x2) * (y1+y2)}")
    
    # Используем первую тройку
    a1, b1, c1 = triples_p1[0]
    a2, b2, c2 = triples_p2[0]
    
    print(f"\nИспользуем тройку Бивера:")
    print(f"  Сторона 1: ({a1}, {b1}, {c1})")
    print(f"  Сторона 2: ({a2}, {b2}, {c2})")
    
    # Протокол MPC-умножения:
    # 1. Каждая сторона вычисляет разности
    d1 = (x1 - a1) % config.MPC_MODULO
    d2 = (x2 - a2) % config.MPC_MODULO
    e1 = (y1 - b1) % config.MPC_MODULO
    e2 = (y2 - b2) % config.MPC_MODULO
    
    # 2. Открывают d = d1 + d2 и e = e1 + e2
    d = (d1 + d2) % config.MPC_MODULO
    e = (e1 + e2) % config.MPC_MODULO
    
    # 3. Каждая сторона вычисляет свою долю результата
    z1 = (c1 + d * b1 + e * a1) % config.MPC_MODULO
    z2 = (c2 + d * b2 + e * a2 + d * e) % config.MPC_MODULO
    
    # 4. Результат: z = z1 + z2
    z = (z1 + z2) % config.MPC_MODULO
    expected_result = ((x1 + x2) * (y1 + y2)) % config.MPC_MODULO
    
    print(f"\nРезультат MPC-умножения: {z}")
    print(f"Ожидаемый результат: {expected_result}")
    
    if z == expected_result:
        print("✓ MPC-умножение выполнено корректно!")
    else:
        raise ValueError("✗ Ошибка в MPC-умножении!")


if __name__ == '__main__':
    main()
