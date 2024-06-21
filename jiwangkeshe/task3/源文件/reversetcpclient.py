import socket
import sys
import struct
import random

# 读取文件并切割成数据块
def read_and_split_file(file_path, Lmin, Lmax):
    # 打开文本文件并读取内容
    with open(file_path, 'r') as file:
        file_content = file.read()
    blocks = []    # 储存切割后的数据块
    current_start_pos = 0   # 数据块的起点位置
    file_length = len(file_content)   # 获取文本文件的长度

    # 循环切割数据块
    while current_start_pos < file_length:
        block_length = random.randint(Lmin, Lmax)    # 生成随机长度的数据块
        current_end_pos = min(current_start_pos + block_length, file_length)    # 计算数据块结束的位置
        blocks.append(file_content[current_start_pos:current_end_pos])   # 将数据块添加到列表中
        current_start_pos = current_end_pos    # 更新数据块的起点位置

    return blocks   # 返回数据块列表

def receive_packet(socket, length):
    data = b''
    # 循环直到data的长度达到指定的length
    while len(data) < length:
        packet = socket.recv(length - len(data))    # 从套接字中接收剩余所需的数据长度, length-len(data)计算出还需要接收多少字节
        if not packet:
            raise ConnectionError("Sorry, something is wrong!")
        data += packet
    return data

def main(server_ip, server_port, file_path, Lmin, Lmax):
    blocks = read_and_split_file(file_path, Lmin, Lmax)   # 读取文本文件并切割成数据块
    blocks_num = len(blocks)  # 数据块的总数
    # 创建TCP套接字
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # 连接到server端
        client_socket.connect((server_ip, server_port))

        # 构造并发送Initialization数据包到server端
        initialization_packet = struct.pack('!HI', 1, blocks_num)
        client_socket.sendall(initialization_packet)

        # 接收server端的agree数据包
        agree_packet = client_socket.recv(2)
        agree_type = struct.unpack('!H', agree_packet)[0]
        if agree_type != 2:
            print("Sorry, the agree packet is not received from the server.")
            return

        # 发送数据块，并接收server端发送回的reverse数据块
        reverse_blocks = []    # 储存reverse后的数据块
        for i, block in enumerate(blocks):
            block_data = block.encode('ascii')  # 将数据块转换为ASCII编码
            block_data_length = len(block_data)  # 获取数据块长度

            # client端构造并发送reverseRequest数据包
            reverseRequest_packet = struct.pack('!HI', 3, block_data_length) + block_data
            client_socket.sendall(reverseRequest_packet)

            # 接收reverseAnswer数据包
            reverseAnswer_packet = receive_packet(client_socket, 6 + block_data_length)
            reverseAnswer_type, reverse_block_data_length = struct.unpack('!HI', reverseAnswer_packet[:6])
            reverse_block_data = reverseAnswer_packet[6:].decode('ascii')
            if reverseAnswer_type == 4 and reverse_block_data_length == block_data_length:
                print(f"{i + 1}: {reverse_block_data}")
                reverse_blocks.append(reverse_block_data)  # 将reverse后的数据块加入到reverse列表中
            else:
                print("Sorry, receiving reverseAnswer packet failed.")
                return

        # 将reverse后的数据块内容写入到新的内容中
        with open('reverse_' + file_path, 'w') as reversed_file:
            reversed_file.write('\n'.join(reverse_blocks))
    finally:
        client_socket.close()    # 关闭连接

if __name__ == '__main__':
    if len(sys.argv) < 6:
        print("Please input: python reversetcpclient.py <server_ip> <server_port> <file_path> <Lmin> <Lmax>")
        sys.exit(1)

    server_ip = sys.argv[1]
    server_port = int(sys.argv[2])
    file_path = sys.argv[3]    # 获取文件路径
    Lmin = int(sys.argv[4])  # 获取数据块的最小长度
    Lmax = int(sys.argv[5])  # 获取数据块的最大长度
    main(server_ip, server_port, file_path, Lmin, Lmax)
