"""
Проверка целостности контейнера 1С (.cf/.cfe/.epf) перед распаковкой.

Читает заголовок и оглавление контейнера, ищет крупные нулевые зоны (признак
оборванного копирования или скачивания). Печатает вердикт OK / ПОВРЕЖДЁН.

Запуск: python tools/check_cf.py "<путь к .cf>"
"""
import struct
import sys

BLOCK_HEADER_LEN = 31
ZERO_SCAN_CHUNK = 4096


def read_block(f, addr):
    """Читает блок контейнера (цепочку страниц) по адресу."""
    f.seek(addr)
    head = f.read(BLOCK_HEADER_LEN)
    if head[:2] != b'\r\n':
        raise ValueError(f'некорректный заголовок блока по смещению {addr:#x}: {head[:8]!r}')
    data_size = int(head[2:10], 16)
    page_size = int(head[11:19], 16)
    next_addr = int(head[20:28], 16)
    out = bytearray(f.read(min(data_size, page_size)))
    while next_addr and next_addr != 0x7fffffff and len(out) < data_size:
        f.seek(next_addr)
        head = f.read(BLOCK_HEADER_LEN)
        if head[:2] != b'\r\n':
            raise ValueError(f'обрыв цепочки страниц по смещению {next_addr:#x}')
        ds = int(head[2:10], 16)
        ps = int(head[11:19], 16)
        next_addr = int(head[20:28], 16)
        out += f.read(min(ds, ps, data_size - len(out)))
    return bytes(out)


def find_zero_tail(f, size):
    """Возвращает (смещение начала хвостовой нулевой зоны, её длина) или (None, 0)."""
    f.seek(0)
    run = 0
    pos = 0
    start = None
    while True:
        buf = f.read(1 << 20)
        if not buf:
            break
        for i in range(0, len(buf), ZERO_SCAN_CHUNK):
            chunk = buf[i:i + ZERO_SCAN_CHUNK]
            if not any(chunk):
                if run == 0:
                    start = pos + i
                run += len(chunk)
            else:
                run = 0
                start = None
        pos += len(buf)
    if start is not None and start + run >= size - ZERO_SCAN_CHUNK and run > (1 << 20):
        return start, run
    return None, 0


def main(path):
    f = open(path, 'rb')
    f.seek(0, 2)
    size = f.tell()
    f.seek(0)
    next_addr, page_size, ver, _ = struct.unpack('<IIII', f.read(16))
    print(f'файл: {path}')
    print(f'размер: {size} Б, page_size={page_size}, версия хранилища={ver}')

    zero_start, zero_len = find_zero_tail(f, size)
    if zero_len:
        print(f'ПОВРЕЖДЁН: с {zero_start:#x} ({zero_start/1024/1024:.1f} МБ) до конца файла — нули, {zero_len/1024/1024:.1f} МБ')
        print('Файл скопирован не полностью. Нужен целый файл.')
        return 1

    try:
        toc = read_block(f, 16)
    except ValueError as err:
        print(f'ПОВРЕЖДЁН: оглавление не читается — {err}')
        return 1

    elements = []
    for i in range(len(toc) // 12):
        a, b, _c = struct.unpack('<III', toc[i * 12:(i + 1) * 12])
        if a and a != 0x7fffffff:
            elements.append((a, b))
    out_of_file = sum(1 for a, b in elements if a >= size or b >= size)
    print(f'элементов в оглавлении: {len(elements)}, ссылок за пределы файла: {out_of_file}')
    if out_of_file:
        print('ПОВРЕЖДЁН: оглавление ссылается за пределы файла')
        return 1
    print('OK: структура контейнера цела, можно распаковывать')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
