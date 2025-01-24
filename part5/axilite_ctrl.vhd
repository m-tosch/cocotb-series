
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;


-- NOTE: This is a 32 bit implementation only
entity axilite_ctrl is

  generic (
    G_S_AXI_CTRL_DATA_WIDTH  					: integer;
    -- Width of S_AXI address bus. log2(number of registers) + 2
    -- two extra to realize the register addressing pattern 0x4, 0x8, 0xC, 0x10, 0x14 ... etc.
    -- the two extra bits are the LSBs, the actual register number (0,1,2,3,4...etc.) are the rest of the MSBs
    -- Examples: (n_registers|ADDR_WIDTH) -> (2|3), (4|4), (8|5), (16|6), (32|7)
    G_S_AXI_CTRL_ADDR_WIDTH  					: integer;
		-- The number of register are the number of real register that are generated inside the possible address range.
		-- Naturally it must be less or equal the possible number of register addressable via tha address width.
		G_S_AXI_CTRL_NUMBER_OF_REGISTERS 	: integer;
    -- register write access yes=1, no=0 for the reg. index. (all registers are "read" by default)
    -- write access means being able to write to that register via SAXI Lite interface
    -- no write access means being able to write to that register only internally i.e. via i_Regs port
    -- example: saxi write access for reg0 and reg1, none for other registers: "00000011"
    G_S_AXI_CTRL_WRITE_REGISTER				: std_logic_vector(G_S_AXI_CTRL_NUMBER_OF_REGISTERS - 1 downto 0)
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
    -- Write Address Channel

    -- Write address (issued by master, acceped by Slave)
    s_axi_awaddr    : in std_logic_vector(G_S_AXI_CTRL_ADDR_WIDTH-1 downto 0);
    -- Write address valid. This signal indicates that the master signaling
    -- valid write address and control information.
    s_axi_awvalid   : in std_logic;
    -- Write address ready. This signal indicates that the slave is ready
    -- to accept an address and associated control signals.
    s_axi_awready   : out std_logic;

    -- Write Data Channel

    -- Write data (issued by master, acceped by Slave)
    s_axi_wdata     : in std_logic_vector(G_S_AXI_CTRL_DATA_WIDTH-1 downto 0);
    -- Write strobes. This signal indicates which byte lanes hold
    s_axi_wstrb     : in std_logic_vector((G_S_AXI_CTRL_DATA_WIDTH/8)-1 downto 0);
    -- Write valid. This signal indicates that valid write
        -- data and strobes are available.
    s_axi_wvalid    : in std_logic;
    -- Write ready. This signal indicates that the slave
        -- can accept the write data.
    s_axi_wready    : out std_logic;

    -- Read Address Channel

    -- Read address (issued by master, acceped by Slave)
    s_axi_araddr    : in std_logic_vector(G_S_AXI_CTRL_ADDR_WIDTH-1 downto 0);
    -- Read address valid. This signal indicates that the channel
    -- is signaling valid read address and control information.
    s_axi_arvalid   : in std_logic;
    -- Read address ready. This signal indicates that the slave is
    -- ready to accept an address and associated control signals.
    s_axi_arready   : out std_logic;

    -- Read Data Channel

    -- Read data (issued by slave)
    s_axi_rdata     : out std_logic_vector(G_S_AXI_CTRL_DATA_WIDTH-1 downto 0);
    -- Read response. This signal indicates the status of the
    -- read transfer.
    s_axi_rresp     : out std_logic_vector(1 downto 0);
    -- Read valid. This signal indicates that the channel is
    -- signaling the required read data.
    s_axi_rvalid    : out std_logic;
    -- Read ready. This signal indicates that the master can
    -- accept the read data and response information.
    s_axi_rready    : in std_logic;

    -- Write Response Channel

    -- Write response. This signal indicates the status
    -- of the write transaction.
    s_axi_bresp     : out std_logic_vector(1 downto 0);
    -- Write response valid. This signal indicates that the channel
    -- is signaling a valid write response.
    s_axi_bvalid    : out std_logic;
    -- Response ready. This signal indicates that the master
    -- can accept a write response.
    s_axi_bready    : in std_logic;

    ---------------------------------------------------------------------------------------
    -- Ports for all registers
    ---------------------------------------------------------------------------------------
    i_Regs : in std_logic_vector((G_S_AXI_CTRL_NUMBER_OF_REGISTERS*G_S_AXI_CTRL_DATA_WIDTH)-1 downto 0);
    o_Regs : out std_logic_vector((G_S_AXI_CTRL_NUMBER_OF_REGISTERS*G_S_AXI_CTRL_DATA_WIDTH)-1 downto 0)
  );
end entity;


architecture arch_imp of axilite_ctrl is

  -- AXI4LITE signals
  signal axi_awaddr  : std_logic_vector(G_S_AXI_CTRL_ADDR_WIDTH-1 downto 0);
  signal axi_awready  : std_logic;
  signal axi_wready  : std_logic;
  signal axi_bresp  : std_logic_vector(1 downto 0);
  signal axi_bvalid  : std_logic;
  signal axi_araddr  : std_logic_vector(G_S_AXI_CTRL_ADDR_WIDTH-1 downto 0);
  signal axi_arready  : std_logic;
  signal axi_rdata  : std_logic_vector(G_S_AXI_CTRL_DATA_WIDTH-1 downto 0);
  signal axi_rresp  : std_logic_vector(1 downto 0);
  signal axi_rvalid  : std_logic;

  -- C_ADDR_LSB is used for addressing 32 registers/memories
  -- C_ADDR_LSB = 2 for 32 bits (n downto 2)
  -- (C_ADDR_LSB = 3 for 64 bits (n downto 3)) <-- not implemented here
  constant C_ADDR_LSB  : integer := (G_S_AXI_CTRL_DATA_WIDTH/32) + 1;

  constant C_ADDRESSABLE_REGISTER : integer := (2**(G_S_AXI_CTRL_ADDR_WIDTH-2));
  constant C_FALLBACK_READ_VALUE : std_logic_vector((G_S_AXI_CTRL_DATA_WIDTH)-1 downto 0) := (others => '1');

  ------------------------------------------------
  ---- Signals for user logic register space example
  --------------------------------------------------
  signal s_regs : std_logic_vector((G_S_AXI_CTRL_NUMBER_OF_REGISTERS*G_S_AXI_CTRL_DATA_WIDTH)-1 downto 0);

  signal s_slv_reg_rden  : std_logic;
  signal s_slv_reg_wren  : std_logic;
  --signal s_reg_data_out  : std_logic_vector(G_S_AXI_CTRL_DATA_WIDTH-1 downto 0);
  signal s_byte_index  : integer range 0 to (G_S_AXI_CTRL_DATA_WIDTH/8)-1;
  signal s_aw_en    : std_logic;

	signal s_LocalWriteAddress : unsigned(G_S_AXI_CTRL_ADDR_WIDTH-1 downto C_ADDR_LSB);
	signal s_LocalReadAddress  : unsigned(G_S_AXI_CTRL_ADDR_WIDTH-1 downto C_ADDR_LSB);

begin
   -- I/O Connections assignments
  s_axi_awready  <= axi_awready;
  s_axi_wready  <= axi_wready;
  s_axi_bresp    <= axi_bresp;
  s_axi_bvalid  <= axi_bvalid;
  s_axi_arready  <= axi_arready;
  s_axi_rdata    <= axi_rdata;
  s_axi_rresp    <= axi_rresp;
  s_axi_rvalid  <= axi_rvalid;

	-- always map output port registers since every register can always be read from
  process (clk)
  begin
    if rising_edge(clk) then
      if reset_n = '0' then
        o_Regs <= (others=>'0');
      else
        o_Regs <= s_regs;
      end if;
    end if;
  end process;

  -- Implement axi_awready generation
  -- axi_awready is asserted for one clk clock cycle when both
  -- s_axi_awvalid and s_axi_wvalid are asserted. axi_awready is
  -- de-asserted when reset is low.

  process (clk)
  begin
    if rising_edge(clk) then
      if reset_n = '0' then
        axi_awready <= '0';
        s_aw_en <= '1';
      else
        if (axi_awready = '0' and s_axi_awvalid = '1' and s_axi_wvalid = '1' and s_aw_en = '1') then
          -- slave is ready to accept write address when
          -- there is a valid write address and write data
          -- on the write address and data bus. This design
          -- expects no outstanding transactions.
             axi_awready <= '1';
             s_aw_en <= '0';
          elsif (s_axi_bready = '1' and axi_bvalid = '1') then
             s_aw_en <= '1';
             axi_awready <= '0';
        else
          axi_awready <= '0';
        end if;
      end if;
    end if;
  end process;

  -- Implement axi_awaddr latching
  -- This process is used to latch the address when both
  -- s_axi_awvalid and s_axi_wvalid are valid.

  process (clk)
  begin
    if rising_edge(clk) then
      if reset_n = '0' then
        axi_awaddr <= (others => '0');
      else
        if (axi_awready = '0' and s_axi_awvalid = '1' and s_axi_wvalid = '1' and s_aw_en = '1') then
          -- Write Address latching
          axi_awaddr <= s_axi_awaddr;
        end if;
      end if;
    end if;
  end process;

  -- Implement axi_wready generation
  -- axi_wready is asserted for one clk clock cycle when both
  -- s_axi_awvalid and s_axi_wvalid are asserted. axi_wready is
  -- de-asserted when reset is low.

  process (clk)
  begin
    if rising_edge(clk) then
      if reset_n = '0' then
        axi_wready <= '0';
      else
        if (axi_wready = '0' and s_axi_wvalid = '1' and s_axi_awvalid = '1' and s_aw_en = '1') then
            -- slave is ready to accept write data when
            -- there is a valid write address and write data
            -- on the write address and data bus. This design
            -- expects no outstanding transactions.
            axi_wready <= '1';
        else
          axi_wready <= '0';
        end if;
      end if;
    end if;
  end process;


  -- Implement memory mapped register select and write logic generation
  -- The write data is accepted and written to memory mapped registers when
  -- axi_awready, s_axi_wvalid, axi_wready and s_axi_wvalid are asserted. Write strobes are used to
  -- select byte enables of slave registers while writing.
  -- These registers are cleared when reset (active low) is applied.
  -- Slave register write enable is asserted when valid address and data are available
  -- and the slave is ready to accept the write address and write data.
  s_slv_reg_wren <= axi_wready and s_axi_wvalid and axi_awready and s_axi_awvalid ;

	s_LocalWriteAddress <= unsigned(axi_awaddr(G_S_AXI_CTRL_ADDR_WIDTH-1 downto C_ADDR_LSB));

  process (clk)
  begin
		if rising_edge(clk) then
			if reset_n = '0' then
				s_regs <= (others=>'0');
			else

        -- check if the register is inside the valid number of registers
				if(s_LocalWriteAddress < G_S_AXI_CTRL_NUMBER_OF_REGISTERS) then
          -- check if the register is defined with having write access via the SAXI bus
					if G_S_AXI_CTRL_WRITE_REGISTER(to_integer(s_LocalWriteAddress)) = '1' then
						if (s_slv_reg_wren = '1') then

							s_regs(((to_integer(s_LocalWriteAddress)+1)*G_S_AXI_CTRL_DATA_WIDTH)-1 downto to_integer(s_LocalWriteAddress)*G_S_AXI_CTRL_DATA_WIDTH) <= s_axi_wdata;

						end if;
					end if;
				end if;

				-- driving other registers in the same process
				-- if a register is defined with NOT having write access (via AXI4) it is written to via the input registers
				for i in 0 to G_S_AXI_CTRL_WRITE_REGISTER'length-1 loop
					if G_S_AXI_CTRL_WRITE_REGISTER(i) = '0' then
						s_regs((i+1)*G_S_AXI_CTRL_DATA_WIDTH-1 downto i*G_S_AXI_CTRL_DATA_WIDTH) <= i_Regs((i+1)*G_S_AXI_CTRL_DATA_WIDTH-1 downto i*G_S_AXI_CTRL_DATA_WIDTH);
					end if;
				end loop;

			end if;
		end if;
  end process;


  -- Implement write response logic generation
  -- The write response and response valid signals are asserted by the slave
  -- when axi_wready, s_axi_wvalid, axi_wready and s_axi_wvalid are asserted.
  -- This marks the acceptance of address and indicates the status of
  -- write transaction.

  process (clk)
  begin
    if rising_edge(clk) then
      if reset_n = '0' then
        axi_bvalid  <= '0';
        axi_bresp   <= "00"; --need to work more on the responses
      else
        if (axi_awready = '1' and s_axi_awvalid = '1' and axi_wready = '1' and s_axi_wvalid = '1' and axi_bvalid = '0'  ) then
          axi_bvalid <= '1';
          axi_bresp  <= "00";
        elsif (s_axi_bready = '1' and axi_bvalid = '1') then   --check if bready is asserted while bvalid is high)
          axi_bvalid <= '0';                                 -- (there is a possibility that bready is always asserted high)
        end if;
      end if;
    end if;
  end process;

  -- Implement axi_arready generation
  -- axi_arready is asserted for one clk clock cycle when
  -- s_axi_arvalid is asserted. axi_awready is
  -- de-asserted when reset (active low) is asserted.
  -- The read address is also latched when s_axi_arvalid is
  -- asserted. axi_araddr is reset to zero on reset assertion.

  process (clk)
  begin
    if rising_edge(clk) then
      if reset_n = '0' then
        axi_arready <= '0';
        axi_araddr  <= (others => '1');
      else
        if (axi_arready = '0' and s_axi_arvalid = '1') then
          -- indicates that the slave has acceped the valid read address
          axi_arready <= '1';
          -- Read Address latching
          axi_araddr  <= s_axi_araddr;
        else
          axi_arready <= '0';
        end if;
      end if;
    end if;
  end process;

  -- Implement axi_arvalid generation
  -- axi_rvalid is asserted for one clk clock cycle when both
  -- s_axi_arvalid and axi_arready are asserted. The slave registers
  -- data are available on the axi_rdata bus at this instance. The
  -- assertion of axi_rvalid marks the validity of read data on the
  -- bus and axi_rresp indicates the status of read transaction.axi_rvalid
  -- is deasserted on reset (active low). axi_rresp and axi_rdata are
  -- cleared to zero on reset (active low).
  process (clk)
  begin
    if rising_edge(clk) then
      if reset_n = '0' then
        axi_rvalid <= '0';
        axi_rresp  <= "00";
      else
        if (axi_arready = '1' and s_axi_arvalid = '1' and axi_rvalid = '0') then
          -- Valid read data is available at the read data bus
          axi_rvalid <= '1';
          axi_rresp  <= "00"; -- 'OKAY' response
        elsif (axi_rvalid = '1' and s_axi_rready = '1') then
          -- Read data is accepted by the master
          axi_rvalid <= '0';
        end if;
      end if;
    end if;
  end process;

  -- Implement memory mapped register select and read logic generation
  -- Slave register read enable is asserted when valid address is available
  -- and the slave is ready to accept the read address.
  s_slv_reg_rden <= axi_arready and s_axi_arvalid and (not axi_rvalid) ;

	s_LocalReadAddress <= unsigned(axi_araddr(G_S_AXI_CTRL_ADDR_WIDTH-1 downto C_ADDR_LSB));

	-- Output register or memory read data
	process( clk ) is
	begin
    if (rising_edge (clk)) then
      if ( reset_n = '0' ) then
       axi_rdata  <= (others => '0');
      else

        -- When there is a valid read address (s_axi_arvalid) with
        -- acceptance of read address by the slave (axi_arready),
        -- output the read dada
        -- Read address mux
        if (s_slv_reg_rden = '1') then

          -- check if the register is inside the valid number of registers
          if(s_LocalReadAddress < G_S_AXI_CTRL_NUMBER_OF_REGISTERS) then

            axi_rdata <= s_regs(((to_integer(s_LocalReadAddress)+1)*G_S_AXI_CTRL_DATA_WIDTH)-1 downto to_integer(s_LocalReadAddress)*G_S_AXI_CTRL_DATA_WIDTH);     -- register read data

          -- check if the register is outside the valid number of registers
          elsif(s_LocalReadAddress >= G_S_AXI_CTRL_NUMBER_OF_REGISTERS and s_LocalReadAddress < C_ADDRESSABLE_REGISTER) then

            axi_rdata <= C_FALLBACK_READ_VALUE;

          end if;

        end if;
      end if;
    end if;
	end process;


end architecture;
