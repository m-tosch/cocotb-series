from cocotbext.axi import AxiStreamFrame

class AxiStreamImage:
    def __init__(self, data, width, height):
        """
        Initialize the AxiStreamImage with data and  dimensions.

        :param data: pixel data of the image. flattened out
        :param width: Width of the image in pixels
        :param height: Height of the image in pixels
        """
        self.data = data
        self.width = width
        self.height = height
        self.image = self._build()


    def _build(self):
        """
        Generate a frame (i.e. line) with specific tuser settings.

        Append all frames to a list which represents the whole image.

        :return: List of AxiStreamFrame objects representing the image
        """
        # build image
        image = []
        for line_idx in range(self.height):

            # Set tuser to 1 for the first pixel in first line only
            tuser = [1 if line_idx == 0 else 0] + [0] * (self.width - 1)

            # Create frame for the line
            line = AxiStreamFrame(tdata=self.data[line_idx*self.width:(line_idx+1)*self.width], tuser=tuser)

            image.append(line)

        return image


    async def send(self, axis_source):
        """
        Send all single frames (i.e. lines) of the image through the AXI source.

        :param axis_source: The AXI stream source to send data through
        """
        for line in self.image:
            await axis_source.send(line)


    def __eq__(self, other):
        if len(self.image) != len(other.image):
            return False
        return all(frame_lhs == frame_rhs for frame_lhs, frame_rhs in zip(self.image, other))

    def __repr__(self):
        return '\n'.join(f"line {idx}: "+repr(frame) for idx,frame in enumerate(self.image))

    def __len__(self):
        return sum(len(frame) for frame in self.image)

    def __iter__(self):
        return iter(self.image)
