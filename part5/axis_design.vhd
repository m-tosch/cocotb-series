library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.axis_design_package.all;

entity axis_design is
    generic(
        G_DATA_WIDTH         : integer range 0 to 63;
        G_N_COLOR_COMPONENTS : integer range 0 to 3;
        G_PIXEL_PER_CLOCK    : integer range 1 to 4
    );
    port (
      ---------------------------------------------------------------------------------------
      -- Clock and Reset
      ---------------------------------------------------------------------------------------
      clk     : in std_logic;
      reset_n : in std_logic;

      ---------------------------------------------------------------------------------------
      -- Ports of Axi Slave Control Bus
      ---------------------------------------------------------------------------------------
      -- Write Address Channel
      s_axi_ctrl_awaddr   : in std_logic_vector(C_PKG_S_AXI_CTRL_ADDR_WIDTH-1 downto 0);
      s_axi_ctrl_awvalid  : in std_logic;
      s_axi_ctrl_awready  : out std_logic;
      -- Write Data Channel
      s_axi_ctrl_wdata    : in std_logic_vector(C_PKG_S_AXI_CTRL_DATA_WIDTH - 1 downto 0);
      s_axi_ctrl_wstrb    : in std_logic_vector(3 downto 0);
      s_axi_ctrl_wvalid   : in std_logic;
      s_axi_ctrl_wready   : out std_logic;
      -- Read Address Channel
      s_axi_ctrl_araddr   : in std_logic_vector(C_PKG_S_AXI_CTRL_ADDR_WIDTH-1 downto 0);
      s_axi_ctrl_arvalid  : in std_logic;
      s_axi_ctrl_arready  : out std_logic;
      -- Read Data Channel
      s_axi_ctrl_rdata    : out std_logic_vector(C_PKG_S_AXI_CTRL_DATA_WIDTH - 1 downto 0);
      s_axi_ctrl_rresp    : out std_logic_vector(1 downto 0);
      s_axi_ctrl_rvalid   : out std_logic;
      s_axi_ctrl_rready   : in std_logic;
      -- Write Response Channel
      s_axi_ctrl_bresp    : out std_logic_vector(1 downto 0);
      s_axi_ctrl_bvalid   : out std_logic;
      s_axi_ctrl_bready   : in std_logic;

      ---------------------------------------------------------------------------------------
      -- Ports of Axi Slave Video Bus Interface
      ---------------------------------------------------------------------------------------
      s_axis_video_tready : out std_logic;
      s_axis_video_tvalid : in std_logic;
      s_axis_video_tuser  : in std_logic_vector(0 downto 0);
      s_axis_video_tlast  : in std_logic;
      s_axis_video_tdata  : in std_logic_vector(G_PIXEL_PER_CLOCK*G_N_COLOR_COMPONENTS*G_DATA_WIDTH-1 downto 0);

      ---------------------------------------------------------------------------------------
      -- Ports of Axi Master Video Bus Interface
      ---------------------------------------------------------------------------------------
      m_axis_video_tready : in std_logic;
      m_axis_video_tvalid : out std_logic;
      m_axis_video_tuser  : out std_logic_vector(0 downto 0);
      m_axis_video_tlast  : out std_logic;
      m_axis_video_tdata  : out std_logic_vector(G_PIXEL_PER_CLOCK*G_N_COLOR_COMPONENTS*G_DATA_WIDTH-1 downto 0)

    );
end entity;

architecture arch of axis_design is

    -------------------------------------------------------------------------------------------
    -- Constants
    -------------------------------------------------------------------------------------------
    constant C_PIXEL_WIDTH : integer := G_DATA_WIDTH * G_N_COLOR_COMPONENTS;

    -------------------------------------------------------------------------------------------
    -- Component Declaration
    -------------------------------------------------------------------------------------------
    component axilite_ctrl is
      generic (
        ---------------------------------------------------------------------------------------
        -- Generics of Axi Video Interfaces
        ---------------------------------------------------------------------------------------
        G_S_AXI_CTRL_DATA_WIDTH						: integer;
        G_S_AXI_CTRL_ADDR_WIDTH  					: integer;
        G_S_AXI_CTRL_NUMBER_OF_REGISTERS	: integer;
        G_S_AXI_CTRL_WRITE_REGISTER      	: std_logic_vector
      );
      port (
        ---------------------------------------------------------------------------------------
        -- Clock and Reset
        ---------------------------------------------------------------------------------------
        clk             : in std_logic;
        reset_n         : in std_logic;

        ---------------------------------------------------------------------------------------
        -- Ports of Axi Slave Control Bus
        ---------------------------------------------------------------------------------------
        s_axi_awaddr    : in std_logic_vector(G_S_AXI_CTRL_ADDR_WIDTH-1 downto 0);
        s_axi_awvalid   : in std_logic;
        s_axi_awready   : out std_logic;
        s_axi_wdata     : in std_logic_vector(G_S_AXI_CTRL_DATA_WIDTH-1 downto 0);
        s_axi_wstrb     : in std_logic_vector((G_S_AXI_CTRL_DATA_WIDTH/8)-1 downto 0);
        s_axi_wvalid    : in std_logic;
        s_axi_wready    : out std_logic;
        s_axi_araddr    : in std_logic_vector(G_S_AXI_CTRL_ADDR_WIDTH-1 downto 0);
        s_axi_arvalid   : in std_logic;
        s_axi_arready   : out std_logic;
        s_axi_rdata     : out std_logic_vector(G_S_AXI_CTRL_DATA_WIDTH-1 downto 0);
        s_axi_rresp     : out std_logic_vector(1 downto 0);
        s_axi_rvalid    : out std_logic;
        s_axi_rready    : in std_logic;
        s_axi_bresp     : out std_logic_vector(1 downto 0);
        s_axi_bvalid    : out std_logic;
        s_axi_bready    : in std_logic;
        i_Regs          : in std_logic_vector((G_S_AXI_CTRL_NUMBER_OF_REGISTERS*G_S_AXI_CTRL_DATA_WIDTH)-1 downto 0);
        o_Regs          : out std_logic_vector((G_S_AXI_CTRL_NUMBER_OF_REGISTERS*G_S_AXI_CTRL_DATA_WIDTH)-1 downto 0)
      );
    end component;

    -------------------------------------------------------------------------------------------
    -- Signal Declaration
    -------------------------------------------------------------------------------------------

    signal s_InputControlRegister         : std_logic_vector((C_PKG_S_AXI_CTRL_NUMBER_OF_REGISTERS*C_PKG_S_AXI_CTRL_DATA_WIDTH)-1 downto 0);
    signal s_OutputControlRegister        : std_logic_vector((C_PKG_S_AXI_CTRL_NUMBER_OF_REGISTERS*C_PKG_S_AXI_CTRL_DATA_WIDTH)-1 downto 0);

begin

  -------------------------------------------------------------------------------------------
  -- Read only registers
  -------------------------------------------------------------------------------------------
  s_InputControlRegister(1*C_PKG_S_AXI_CTRL_DATA_WIDTH-1 downto 0*C_PKG_S_AXI_CTRL_DATA_WIDTH) <= std_logic_vector(to_unsigned(16#DEAD#, C_PKG_S_AXI_CTRL_DATA_WIDTH));
  s_InputControlRegister(2*C_PKG_S_AXI_CTRL_DATA_WIDTH-1 downto 1*C_PKG_S_AXI_CTRL_DATA_WIDTH) <= std_logic_vector(to_unsigned(16#BEEF#, C_PKG_S_AXI_CTRL_DATA_WIDTH));

  -------------------------------------------------------------------------------------------
  -- Instantiations
  -------------------------------------------------------------------------------------------
  inst_axilite_ctrl : axilite_ctrl
  generic map (
    G_S_AXI_CTRL_DATA_WIDTH  					=> C_PKG_S_AXI_CTRL_DATA_WIDTH,
    G_S_AXI_CTRL_ADDR_WIDTH  					=> C_PKG_S_AXI_CTRL_ADDR_WIDTH,
    G_S_AXI_CTRL_WRITE_REGISTER       => C_PKG_S_AXI_CTRL_WRITE_REGISTER,
		G_S_AXI_CTRL_NUMBER_OF_REGISTERS	=> C_PKG_S_AXI_CTRL_NUMBER_OF_REGISTERS
  )
  port map (
    ---------------------------------------------------------------------------------------
    -- Clock and Reset
    ---------------------------------------------------------------------------------------
    clk            => clk,
    reset_n        => reset_n,

    ---------------------------------------------------------------------------------------
    -- Ports of Control Interface
    ---------------------------------------------------------------------------------------
    s_axi_awaddr   => s_axi_ctrl_awaddr,
    s_axi_awvalid  => s_axi_ctrl_awvalid,
    s_axi_awready  => s_axi_ctrl_awready,
    s_axi_wdata    => s_axi_ctrl_wdata,
    s_axi_wstrb    => s_axi_ctrl_wstrb,
    s_axi_wvalid   => s_axi_ctrl_wvalid,
    s_axi_wready   => s_axi_ctrl_wready,
    s_axi_araddr   => s_axi_ctrl_araddr,
    s_axi_arvalid  => s_axi_ctrl_arvalid,
    s_axi_arready  => s_axi_ctrl_arready,
    s_axi_rdata    => s_axi_ctrl_rdata,
    s_axi_rresp    => s_axi_ctrl_rresp,
    s_axi_rvalid   => s_axi_ctrl_rvalid,
    s_axi_rready   => s_axi_ctrl_rready,
    s_axi_bresp    => s_axi_ctrl_bresp,
    s_axi_bvalid   => s_axi_ctrl_bvalid,
    s_axi_bready   => s_axi_ctrl_bready,
    i_Regs         => s_InputControlRegister,
    o_Regs         => s_OutputControlRegister
  );


    ppc_1 : if G_PIXEL_PER_CLOCK = 1 generate
        m_axis_video_tdata <= std_logic_vector(unsigned(s_axis_video_tdata) + 1);
    end generate;

    ppc_2 : if G_PIXEL_PER_CLOCK = 2 generate
        m_axis_video_tdata(1*C_PIXEL_WIDTH-1 downto 0*C_PIXEL_WIDTH) <= std_logic_vector(unsigned(s_axis_video_tdata(1*C_PIXEL_WIDTH-1 downto 0*C_PIXEL_WIDTH)) + 1);
        m_axis_video_tdata(2*C_PIXEL_WIDTH-1 downto 1*C_PIXEL_WIDTH) <= std_logic_vector(unsigned(s_axis_video_tdata(2*C_PIXEL_WIDTH-1 downto 1*C_PIXEL_WIDTH)) + 1);
    end generate;

    ppc_4 : if G_PIXEL_PER_CLOCK = 4 generate
      m_axis_video_tdata(1*C_PIXEL_WIDTH-1 downto 0*C_PIXEL_WIDTH) <= std_logic_vector(unsigned(s_axis_video_tdata(1*C_PIXEL_WIDTH-1 downto 0*C_PIXEL_WIDTH)) + 1);
      m_axis_video_tdata(2*C_PIXEL_WIDTH-1 downto 1*C_PIXEL_WIDTH) <= std_logic_vector(unsigned(s_axis_video_tdata(2*C_PIXEL_WIDTH-1 downto 1*C_PIXEL_WIDTH)) + 1);
      m_axis_video_tdata(3*C_PIXEL_WIDTH-1 downto 2*C_PIXEL_WIDTH) <= std_logic_vector(unsigned(s_axis_video_tdata(3*C_PIXEL_WIDTH-1 downto 2*C_PIXEL_WIDTH)) + 1);
      m_axis_video_tdata(4*C_PIXEL_WIDTH-1 downto 3*C_PIXEL_WIDTH) <= std_logic_vector(unsigned(s_axis_video_tdata(4*C_PIXEL_WIDTH-1 downto 3*C_PIXEL_WIDTH)) + 1);
    end generate;

    m_axis_video_tuser  <= s_axis_video_tuser;
    m_axis_video_tlast  <= s_axis_video_tlast;
    m_axis_video_tvalid <= s_axis_video_tvalid;
    s_axis_video_tready <= m_axis_video_tready;

end architecture;