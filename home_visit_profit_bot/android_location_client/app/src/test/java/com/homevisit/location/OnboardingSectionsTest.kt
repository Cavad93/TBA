package com.homevisit.location

import com.homevisit.location.domain.SettingField
import com.homevisit.location.domain.SettingType
import com.homevisit.location.domain.SettingsSection
import org.junit.Assert.assertEquals
import org.junit.Test

/** Онбординг: зоны не рендерятся как обычная секция (у них свой шаг мастера с
 *  редактором область→город→районы, а не поле в общем списке настроек). */
class OnboardingSectionsTest {

    @Test
    fun `секция из одних зон выпадает, смешанная и обычная остаются`() {
        val zonesOnly = SettingsSection(
            key = "base",
            title = "Зоны",
            fields = listOf(SettingField(key = "base_zones", label = "Зоны", type = SettingType.Zones)),
        )
        val money = SettingsSection(
            key = "money",
            title = "Деньги",
            fields = listOf(SettingField(key = "min_hourly_income", label = "Планка", type = SettingType.Number)),
        )
        val mixed = SettingsSection(
            key = "mixed",
            title = "Смешанная",
            fields = listOf(
                SettingField(key = "base_zones", label = "Зоны", type = SettingType.Zones),
                SettingField(key = "transport_type", label = "Транспорт", type = SettingType.Choice),
            ),
        )

        val result = onboardingSections(listOf(zonesOnly, money, mixed))

        assertEquals(listOf("money", "mixed"), result.map { it.key })
    }
}
