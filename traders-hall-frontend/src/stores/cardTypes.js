import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

/**
 * The card catalogue, fetched once from the backend.
 *
 * This replaces the hardcoded `cards` object that used to live in Card.vue.
 * One source of truth: the cost the server charges and the cost the UI shows
 * are now the same number by construction.
 */
export const useCardTypesStore = defineStore('cardTypes', () => {
  // ---- state ----
  const byCode = ref({})        // { house: {...}, rice: {...}, ... }
  const loaded = ref(false)     // true once a fetch has succeeded
  const loading = ref(false)    // true while a fetch is in flight
  const error = ref(null)

  // ---- getters ----
  // sorted list, for anywhere that needs to iterate the catalogue
  const all = computed(() =>
    Object.values(byCode.value).sort((a, b) => a.sortOrder - b.sortOrder)
  )

  // ---- actions ----
  async function fetchAll() {
    // already have it, or a request is already running — don't refetch
    if (loaded.value || loading.value) return

    loading.value = true
    error.value = null

    try {
      const response = await fetch('/api/v1/config/card-types')
      if (!response.ok) {
        throw new Error(`Failed to load card types (HTTP ${response.status})`)
      }

      const list = await response.json()

      // The API speaks snake_case; the frontend speaks camelCase. Translating
      // here, at the boundary, means no component ever has to know that.
      byCode.value = Object.fromEntries(
        list.map((c) => [
          c.code,
          {
            code: c.code,
            title: c.title,
            category: c.category,
            baseCost: c.base_cost,
            sellValue: c.sell_value,
            nutritionTurns: c.nutrition_turns,
            baseOutputPoints: c.base_output_points,
            iconUrl: c.icon_url,
            accentColor: c.accent_color,
            backgroundColor: c.background_color,
            isTradeable: c.is_tradeable,
            sortOrder: c.sort_order,
          },
        ])
      )

      loaded.value = true
    } catch (e) {
      error.value = e.message ?? 'Unknown error'
    } finally {
      loading.value = false
    }
  }

  /** Look up one card type. Returns undefined if unknown. */
  function get(code) {
    return byCode.value[code]
  }

  return { byCode, loaded, loading, error, all, fetchAll, get }
})