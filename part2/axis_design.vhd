library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity axis_design is
    generic(
        G_DATA_WIDTH         : integer range 0 to 63;
        G_N_COLOR_COMPONENTS : integer range 0 to 3
    );
    port(
      ---------------------------------------------------------------------------------------
      -- Clock and Reset
      ---------------------------------------------------------------------------------------
      clk     : in std_logic;
      reset_n : in std_logic;

      ---------------------------------------------------------------------------------------
      -- Ports of Axi Slave Video Bus Interface
      ---------------------------------------------------------------------------------------
      s_axis_video_tready : out std_logic;
      s_axis_video_tvalid : in std_logic;
      s_axis_video_tuser  : in std_logic_vector(0 downto 0);
      s_axis_video_tlast  : in std_logic;
      s_axis_video_tdata  : in std_logic_vector(G_N_COLOR_COMPONENTS*G_DATA_WIDTH-1 downto 0);

      ---------------------------------------------------------------------------------------
      -- Ports of Axi Master Video Bus Interface
      ---------------------------------------------------------------------------------------
      m_axis_video_tready : in std_logic;
      m_axis_video_tvalid : out std_logic;
      m_axis_video_tuser  : out std_logic_vector(0 downto 0);
      m_axis_video_tlast  : out std_logic;
      m_axis_video_tdata  : out std_logic_vector(G_N_COLOR_COMPONENTS*G_DATA_WIDTH-1 downto 0)

    );
end entity;

architecture arch of axis_design is

begin

    m_axis_video_tdata  <= s_axis_video_tdata;
    m_axis_video_tuser  <= s_axis_video_tuser;
    m_axis_video_tlast  <= s_axis_video_tlast;
    m_axis_video_tvalid <= s_axis_video_tvalid;
    s_axis_video_tready <= m_axis_video_tready;

end architecture;