import socket
import struct
import threading

# 服务器配置
SERVER_IP = '127.0.0.1'  # 本机IP地址
# SERVER_IP = '172.26.160.130'  # 本机IP地址
SERVER_PORT = 12345  # 服务器端口号

def receive_packet(socket, length):
    data = b''
    while len(data) < length:
        packet = socket.recv(length - len(data))
        if not packet:
            raise ConnectionError("Sorry, something is wrong!")
        data += packet
    return data

# 处理客户端连接
def process_client_connection(client_socket):
    try:
        # 接收Initialization数据包，并解析出其类型以及块数
        initialization_packet = receive_packet(client_socket, 6)
        initialization_type, blocks_num = struct.unpack('!HI', initialization_packet)
        if initialization_type != 1:
            return

        # 创建并发送agree数据包
        agree_packet = struct.pack('!H', 2)
        client_socket.sendall(agree_packet)

        # 循环接收并reverse每一个数据块，并发送回client端
        for _ in range(blocks_num):
            # 接收reverseRequest数据包，并解析数据包类型和数据长度
            reverseRequest_packet = receive_packet(client_socket, 6)
            reverseRequest_type, block_data_length = struct.unpack('!HI', reverseRequest_packet)
            if reverseRequest_type != 3:
                print("Wrong reverseRequest type!")
                return

            # 接收数据块
            block_data = receive_packet(client_socket, block_data_length)
            # 反转数据块的内容
            reverse_block_data = block_data.decode('ascii')[::-1].encode('ascii')

            # 创建并发送reverseAnswer数据包给client端
            reverseAnswer_packet = struct.pack('!HI', 4, block_data_length) + reverse_block_data
            client_socket.sendall(reverseAnswer_packet)
    except Exception as err:
        print(f"ERROR: {err}")
    finally:
        client_socket.close()   # 关闭连接

def main():
    # 创建TCP套接字
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((SERVER_IP, SERVER_PORT))   # 绑定到指定的IP地址和端口
    server_socket.listen(4)    # 开始监听Client端连接
    print(f"Server is listening on {SERVER_IP}:{SERVER_PORT}！")

    while True:
        client_socket, addr = server_socket.accept()   # 接收Client端的连接
        client_connection = threading.Thread(target = process_client_connection, args = (client_socket,))  # 创建线程处理Client端连接
        client_connection.start()  # 启动线程

if __name__ == '__main__':
    main()
