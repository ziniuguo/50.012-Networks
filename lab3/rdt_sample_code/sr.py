import config
import threading
import time
import udt
import util


# Go-Back-N reliable transport protocol.
class SelectiveRepeat:

	# "msg_handler" is used to deliver messages to application layer
	def __init__(self, local_port, remote_port, msg_handler):
		util.log("Starting up `Selective Repeat` protocol ... ")
		self.network_layer = udt.NetworkLayer(local_port, remote_port, self)
		self.msg_handler = msg_handler
		self.sender_base = 0
		self.receiver_base = 0
		self.next_sequence_number = 0
		self.timers = [self.get_timer(-1)] * config.WINDOW_SIZE  # timer list
		self.acks = [False] * config.WINDOW_SIZE  # sender buffer controller
		self.window = [b''] * config.WINDOW_SIZE  # sender buffer
		self.rcvs = [False] * config.WINDOW_SIZE  # receiver buffer controller
		self.rcv_window = [b''] * config.WINDOW_SIZE  # receiver buffer
		self.is_receiver = True
		self.sender_lock = threading.Lock()

	def get_timer(self, i):
		return threading.Timer((config.TIMEOUT_MSEC / 1000.0), self._timeout, [i])  # param of timeout func

	def _timeout(self, i):
		func_name = "_timeout: "
		util.log(func_name + "Timeout! Resending below packets: " + str(i))
		self.sender_lock.acquire()
		rsd_pkt_idx = (i - self.sender_base) % config.WINDOW_SIZE
		self.timers[rsd_pkt_idx].cancel()
		self.timers[rsd_pkt_idx] = self.get_timer(i)
		rsd = self.window[rsd_pkt_idx]
		self.network_layer.send(rsd)
		util.log(func_name + "Resending packet: " + util.pkt_to_string(util.extract_data(rsd)))
		self.timers[rsd_pkt_idx].start()
		self.sender_lock.release()
		return

	# "send" is called by application. Return true on success, false otherwise.
	def send(self, msg):
		self.is_receiver = False
		if self.next_sequence_number < (self.sender_base + config.WINDOW_SIZE):
			self._send_helper(msg)
			return True
		else:
			util.log("Window is full. App data rejected.")
			time.sleep(1)
			return False

	# Helper fn for thread to send the next packet
	def _send_helper(self, msg):
		func_name = "_send_helper: "
		self.sender_lock.acquire()
		packet_bytes = util.make_packet(msg, config.MSG_TYPE_DATA, self.next_sequence_number)
		packet_data = util.extract_data(packet_bytes)
		util.log(func_name + "Sending data: " + util.pkt_to_string(packet_data))
		self.network_layer.send(packet_bytes)

		# need to change window
		if self.next_sequence_number < self.sender_base + config.WINDOW_SIZE:
			# get window loc
			curr_pkt_idx = (self.next_sequence_number - self.sender_base) % config.WINDOW_SIZE
			self.window[curr_pkt_idx] = packet_bytes
			# self.acks[curr_pkt_idx] = False  # by default it is false
			self.timers[curr_pkt_idx] = self.get_timer(self.next_sequence_number)  # start timer for this packet
			self.timers[curr_pkt_idx].start()
			self.next_sequence_number += 1
		self.sender_lock.release()
		return

	# "handler" to be called by network layer when packet is ready.
	def handle_arrival_msg(self):
		func_name = "handel_arrival_msg: "
		msg = self.network_layer.recv()
		msg_data = util.extract_data(msg)
		if msg_data.is_corrupt:
			# ignore
			# do nothing. If not receiver, we ignore it. If is receiver, we do not send last ack.
			return

		# If ACK message, assume it is for sender
		if msg_data.msg_type == config.MSG_TYPE_ACK:
			self.sender_lock.acquire()
			ack_idx = (msg_data.seq_num - self.sender_base) % config.WINDOW_SIZE
			self.acks[ack_idx] = True
			# reset timer
			self.timers[ack_idx].cancel()

			# update all lists, move window
			while self.acks[0]:
				self.sender_base += 1
				util.log(func_name + "sender_base: " + str(self.sender_base - 1) + " -> " + str(self.sender_base))
				self.acks = self.acks[1:] + [False]  # remove the first one, append False to the end
				self.window = self.window[1:] + [b'']
				self.timers = self.timers[1:] + [self.get_timer(-1)]  # same as above

			self.sender_lock.release()
		# If DATA message, assume it is for receiver
		else:
			assert msg_data.msg_type == config.MSG_TYPE_DATA
			ack_pkt = util.make_packet(b'', config.MSG_TYPE_ACK, msg_data.seq_num)
			util.log("Sending ACK: " + util.pkt_to_string(util.extract_data(ack_pkt)))
			self.network_layer.send(ack_pkt)  # send ack

			if self.receiver_base <= msg_data.seq_num < self.receiver_base + config.WINDOW_SIZE:
				curr_pkt_idx = (msg_data.seq_num - self.receiver_base) % config.WINDOW_SIZE
				self.rcvs[curr_pkt_idx] = True  # change it to True to indicate receive
				self.rcv_window[curr_pkt_idx] = msg_data.payload
				if msg_data.seq_num == self.receiver_base:
					while self.rcvs[0]:  # do the same thing
						self.msg_handler(self.rcv_window[0])
						self.receiver_base += 1
						util.log(func_name + "receiver_base: " + str(self.receiver_base - 1) + " -> " + str(
							self.receiver_base))
						self.rcv_window = self.rcv_window[1:] + [b'']
						self.rcvs = self.rcvs[1:] + [False]
		return

	# Cleanup resources.
	def shutdown(self):
		if not self.is_receiver:
			self._wait_for_last_ack()
		for timer in self.timers:
			if timer.is_alive():
				timer.cancel()
		util.log("Connection shutting down...")
		self.network_layer.shutdown()

	def _wait_for_last_ack(self):
		while self.sender_base < self.next_sequence_number - 1:
			util.log(
				"Waiting for last ACK from receiver with sequence # " + str(int(self.next_sequence_number - 1)) + ".")
			time.sleep(1)
