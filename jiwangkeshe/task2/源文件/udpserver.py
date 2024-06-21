import socket
import random
import time

# 服务器配置
# SERVER_IP = '127.0.0.1'  # 本机IP地址
SERVER_IP = '192.168.233.128'  # 本机IP地址
# SERVER_IP = '172.26.160.130'  # 本机IP地址
SERVER_PORT = 12345  # 服务器端口号
PACKETSDROPED_RATE = 0.3  # 丢包率
REQUESTS_RECEIVED = 12  # 要接收的请求数

# 数据包格式
HEADER_SIZE = 203  # 头部大小
DATA_SIZE = 0  # 数据部分大小，因为187字节是填充，不包含实际数据

# 获取当前时间字符串
def currenttime_acquired():
    current_time = int(time.time()).to_bytes(8, 'big')
    return current_time

# 创建数据包
def resppacket_creat(seq_no, version, data_len, resp_type):
    resp_filling = b'a' * 187
    system_time = currenttime_acquired()
    server_status_code = (200).to_bytes(2, 'big')
    return (
            seq_no.to_bytes(2, 'big') +
            bytes([version]) +
            system_time +
            data_len.to_bytes(2, 'big') +
            bytes([resp_type]) +  # 响应类型
            server_status_code +  # 服务器状态码
            resp_filling
    )

def main():
    # 创建UDP套接字
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((SERVER_IP, SERVER_PORT))  # 绑定IP和端口
    print(f"Server is listening on {SERVER_IP}:{SERVER_PORT}！")

    while True:
        try:
            # 接收来自client端的数据包
            packet, client_address = server_socket.recvfrom(HEADER_SIZE + DATA_SIZE)
            seq_no, version, data_len, req_type = int.from_bytes(packet[:2], 'big'), packet[2], int.from_bytes(packet[3:5],'big'), packet[5]

            if req_type == 1:  # 接收到client端的SYN
                # 构造SYN-ACK响应数据包，发送SYN-ACK响应给客户端
                syn_ack_packet = resppacket_creat(seq_no, version, data_len, 2)  # SYN-ACK
                server_socket.sendto(syn_ack_packet, client_address)

            elif req_type == 3:  # 接收到client端的ACK
                # 进入数据传输阶段
                for _ in range(REQUESTS_RECEIVED):
                    packet, client_address = server_socket.recvfrom(HEADER_SIZE + DATA_SIZE)
                    seq_no, version, data_len = int.from_bytes(packet[:2], 'big'), packet[2], int.from_bytes(packet[3:5],'big')

                    # 模拟丢包
                    if random.random() < PACKETSDROPED_RATE:
                        continue

                    # 构造并发送响应数据包给client端
                    resp_packet = resppacket_creat(seq_no, version, data_len, 4)  # 响应状态
                    server_socket.sendto(resp_packet, client_address)

            elif req_type == 5:  # 接收到client端的FIN
                # 构造FIN-ACK响应数据包，发送FIN-ACK响应给client端
                fin_ack_packet = resppacket_creat(seq_no, version, data_len, 6)  # FIN-ACK
                server_socket.sendto(fin_ack_packet, client_address)
                # 构造服务器FIN包，发送服务器FIN包给client端
                server_fin_packet = resppacket_creat(seq_no, version, data_len, 7)  # Server的FIN
                server_socket.sendto(server_fin_packet, client_address)

                # 等待ACK确认
                ack_packet, _ = server_socket.recvfrom(HEADER_SIZE + DATA_SIZE)    # 接收client端的LAST_ACK数据包
                if ack_packet[5] == 8:  # ACK
                    print("Congratulations! Connection closed successfully.")
                    break

        except KeyboardInterrupt:
            print("The server is shutting down.")
            break

if __name__ == '__main__':
    main()