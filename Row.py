class Row():
  INTRO = "I"
  EXTRO = "E"
  METHOD = "M"
  
  def __init__(self, row_id, frame_length):
    self.row_id = row_id
    self.row_type = row_id[0:1]
    self.row_number = int(row_id[1:5])
    self.bell_order = []
    self.call_go = False
    self.call_thats_all = False
    self.call_bob = False
    self.call_single = False
    self.call_stand = False
    if (self.row_type == Row.METHOD or self.row_type == Row.EXTRO) and (self.row_number - 1) % frame_length == 0:
      self.frame_start = True
    else:
      self.frame_start = False
  
  def add_bell(self, bell_id):
    self.bell_order.append(bell_id)
