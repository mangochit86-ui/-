package com.example.blackhole;

import net.fabricmc.api.ModInitializer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class BlackHoleMod implements ModInitializer {
    public static final String MOD_ID = "blackhole";
    public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

    @Override
    public void onInitialize() {
        ModItems.init();
        ModLootTables.init();
        LOGGER.info("Black Hole mod loaded");
    }
}
