package com.example.blackhole;

import java.util.function.Function;

import net.fabricmc.fabric.api.itemgroup.v1.ItemGroupEvents;
import net.minecraft.item.Item;
import net.minecraft.item.ItemGroups;
import net.minecraft.registry.Registries;
import net.minecraft.registry.Registry;
import net.minecraft.registry.RegistryKey;
import net.minecraft.registry.RegistryKeys;
import net.minecraft.util.Identifier;
import net.minecraft.util.Rarity;

public final class ModItems {
    private ModItems() {
    }

    /** Stage 2: crafting ingredient. 8 of them craft the Black Hole. */
    public static final Item BLACK_HOLE_FRAGMENT = register(
            "black_hole_fragment",
            Item::new,
            new Item.Settings().rarity(Rarity.RARE));

    /** Stage 1: the item itself. Behaviour comes in the next stages. */
    public static final Item BLACK_HOLE = register(
            "black_hole",
            Item::new,
            new Item.Settings().maxCount(1).rarity(Rarity.EPIC));

    private static Item register(String name, Function<Item.Settings, Item> factory, Item.Settings settings) {
        RegistryKey<Item> key = RegistryKey.of(RegistryKeys.ITEM, Identifier.of(BlackHoleMod.MOD_ID, name));
        return Registry.register(Registries.ITEM, key, factory.apply(settings.registryKey(key)));
    }

    public static void init() {
        ItemGroupEvents.modifyEntriesEvent(ItemGroups.INGREDIENTS).register(entries -> {
            entries.add(BLACK_HOLE_FRAGMENT);
            entries.add(BLACK_HOLE);
        });
    }
}
