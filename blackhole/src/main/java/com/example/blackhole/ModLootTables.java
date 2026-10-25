package com.example.blackhole;

import net.fabricmc.fabric.api.loot.v3.LootTableEvents;
import net.minecraft.loot.LootPool;
import net.minecraft.loot.condition.RandomChanceLootCondition;
import net.minecraft.loot.entry.ItemEntry;
import net.minecraft.loot.provider.number.ConstantLootNumberProvider;

/** Adds black hole fragments to the vanilla chest loot tables. */
public final class ModLootTables {
    private ModLootTables() {
    }

    /** Chance that one chest contains a fragment: 0.005 = 0.5%. Change it here. */
    public static final float FRAGMENT_CHEST_CHANCE = 0.005f;

    public static void init() {
        LootTableEvents.MODIFY.register((key, tableBuilder, source, registries) -> {
            if (!source.isBuiltin()) {
                return;
            }
            if (!key.getValue().getPath().startsWith("chests/")) {
                return;
            }
            tableBuilder.pool(LootPool.builder()
                    .rolls(ConstantLootNumberProvider.create(1.0f))
                    .conditionally(RandomChanceLootCondition.builder(FRAGMENT_CHEST_CHANCE))
                    .with(ItemEntry.builder(ModItems.BLACK_HOLE_FRAGMENT)));
        });
    }
}
