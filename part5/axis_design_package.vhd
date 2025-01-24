library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

package axis_design_package is

  constant C_PKG_S_AXI_CTRL_DATA_WIDTH          : integer          := 32;
  constant C_PKG_S_AXI_CTRL_NUMBER_OF_REGISTERS : integer          := 4;
  constant C_PKG_S_AXI_CTRL_WRITE_REGISTER      : std_logic_vector := "1100"; -- registers 3,2 are r/w. registers 1,0 are read-only
  constant C_PKG_S_AXI_CTRL_ADDR_WIDTH          : integer          := 4; -- log2(NUMBER_OF_REGISTERS), but + 2 = 4

end package;