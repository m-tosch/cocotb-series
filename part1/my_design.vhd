library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity my_design is
    generic(
        G_DATA_WIDTH : integer range 0 to 63
    );
    port (
        clk     : in std_logic;
        reset_n : in std_logic;
        i_Data  : in std_logic_vector(G_DATA_WIDTH-1 downto 0)
    );
end entity;

architecture arch of my_design is

    signal s_signal_1 : std_logic := 'X'; -- uninitialized state
    signal s_signal_2 : std_logic := '0'; -- initialized to logic 0

    signal s_Data : std_logic_vector(G_DATA_WIDTH-1 downto 0) := (others => 'X');

begin

    proc_Process: process(clk)
    begin
    if (rising_edge (clk)) then
      if (reset_n = '0') then
        s_Data <= (others => '0');
      else
        s_Data <= i_Data;
      end if;
    end if;
    end process;

end architecture;