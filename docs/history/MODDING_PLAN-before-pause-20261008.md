# Beyond Good and Evil — resource research plan

Install: E:/SteamLibrary/steamapps/common/Beyond Good and Evil - 20th Anniversary Edition, Steam app 2556990.
Code: native x64 PE, image base 0x140000000. Engine: Jade, identified by the user; exact remaster revision is not yet established.
Recon: um scan found no anti-cheat signals and no installed mod loader; this is a bounded scan result.

Current route: read-only archive analysis before selecting any hook or loader. The concrete resource format is BPAK (.pak), opened and indexed by FUN_140ae6ad0. Its serialized index topology has been verified against all 23 installed archives.

Evidence, addresses, unknowns and validation are recorded in MODLOG.md. Run inspect_pak_index.py to repeat index validation; it writes pak-index-validation.json and does not alter the game.

Next milestone: recover 68-byte TXI records and TXS string buffers; all 150 language tables and 300 English/Russian keys are now mapped; then decode one small asset and verify its output. Choose a writer or native hook only when a specific modification requires it.



