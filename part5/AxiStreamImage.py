from cocotbext.axi import AxiStreamFrame

class AxiStreamImage:

    def __init__(self, data, width, height, axis_frames=None):
        """
        Initialize the AxiStreamImage with data and dimensions or from a list of AxiStreamFrame

        :param data: all image pixel data. flattened out into a 1D list
        :param width: Width of the image in pixels
        :param height: Height of the image in pixels
        :param axis_frames: (optional) list of AxiStreamFrame
        """
        self.width = width
        self.height = height
        if axis_frames is None:
            self.axis_frames = self._build(data)
        else:
            self.axis_frames = axis_frames


    @classmethod
    def from_frames(cls, axis_frames):
        """
        Initialize the AxiStreamImage from a list of AxiStreamFrame

        :param axis_frames: list of AxiStreamFrame
        """
        width = len(axis_frames[0])
        height = len(axis_frames)
        return cls(None, width, height, axis_frames)


    def _build(self, data):
        """
        Generate a frame (i.e. line) with specific tuser settings.

        Append all frames to a list which represents the whole image.

        :return: List of AxiStreamFrame objects representing the image
        """
        # build image
        axis_frames = []
        for line_idx in range(self.height):

            # Set tuser to 1 for the first pixel in first line only
            tuser = [1 if line_idx == 0 else 0] + [0] * (self.width - 1)

            # Create frame for the line
            line = AxiStreamFrame(tdata=data[line_idx*self.width:(line_idx+1)*self.width], tuser=tuser)

            axis_frames.append(line)

        return axis_frames


    async def send(self, axis_source):
        """
        Send all single frames (i.e. lines) of the image through the AXI stream.

        :param axis_source: The AXI stream source to send data through
        """
        for line in self.axis_frames:
            await axis_source.send(line)


    def data(self):
        """
        Get a singular list of all individual pixel values from all frames (i.e. lines)

        :return: A list of all pixel values
        """
        return sum([af.tdata for af in self.axis_frames], [])


    def __eq__(self, other):
        return all(frame0 == frame1 for frame0, frame1 in zip(self.axis_frames, other))


    def __repr__(self):
        frames = '\n'.join(f"line {idx}: "+repr(frame) for idx,frame in enumerate(self.axis_frames))
        return f"{'*' * 18} [{self.__class__.__name__}] {'*' * 18}\n{frames}\n{'*' * 18} {'*' * 16} {'*' * 18}\n"


    def __len__(self):
        return sum(len(frame) for frame in self.axis_frames)


    def __iter__(self):
        return iter(self.axis_frames)


    def __getitem__(self, index):
        if not isinstance(index, int):
            raise TypeError("Index must be an integer")

        if index < 0:
            index += len(self.axis_frames)  # Handle negative indexing

        if index >= len(self.axis_frames) or index < 0:
            raise IndexError("Index out of range")

        return self.axis_frames[index]


    def __setitem__(self, index, value):
        if not isinstance(index, int):
            raise TypeError("Index must be an integer")
        if index < 0:
            index += len(self.axis_frames) + 1  # +1 because we extend if index is out of range

        # If the index is beyond the current length, extend the list
        if index >= len(self.axis_frames):
            self.axis_frames.extend([None] * (index - len(self.axis_frames) + 1))

        self.axis_frames[index] = value