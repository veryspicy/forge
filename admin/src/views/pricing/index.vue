<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { ref, onMounted, h } from 'vue';
import {
  NButton, NCard, NDataTable, NForm, NFormItem, NInput, NInputNumber,
  NModal, NSelect, NSpace, NSwitch, NTabPane, NTabs, NTag,
} from 'naive-ui';
import { get, post, patch, del } from '@/service/api/helper';
import type { DataTableColumns } from 'naive-ui';

const tab = ref('rules');
const rules = ref<any[]>([]);
const promotions = ref<any[]>([]);

// Calculator
const calc = ref({ product_id: '', cost_price: 0, region: 'AE', override_price: null as number | null });
const calcResult = ref<Record<string, any> | null>(null);
const calcLoading = ref(false);
const regionOpts = ['AE', 'SA', 'KW', 'QA', 'OM', 'BH'].map(v => ({ label: v, value: v }));

// Rule modal
const showRuleModal = ref(false);
const editingRule = ref<any>(null);
const ruleForm = ref({ name: '', region: 'GLOBAL', markup_multiplier: 1.4, fixed_shipping_fee: 5.0, priority: 0, is_active: true, is_default: false });

// Promo modal
const showPromoModal = ref(false);
const editingPromo = ref<any>(null);
const promoForm = ref({ name: '', type: 'COUPON', applicable_regions: [] as string[], applicable_categories: [] as string[], start_date: '', end_date: '', is_active: true, stackable: false, priority: 0 });
const promoRegions = ref('');
const promoCategories = ref('');
const promoTypeOptions: any[] = [
  { label: () => t('page.pricing.coupon'), value: 'COUPON' },
  { label: () => t('page.pricing.discount'), value: 'DISCOUNT' },
  { label: () => t('page.pricing.bundle'), value: 'BUNDLE' },
];

const modalError = ref('');
const modalLoading = ref(false);
const { t } = useI18n();

function updatePromoRegions() { promoForm.value.applicable_regions = promoRegions.value.split(',').map(s => s.trim()).filter(Boolean); }
function updatePromoCats() { promoForm.value.applicable_categories = promoCategories.value.split(',').map(s => s.trim()).filter(Boolean); }

const ruleColumns: DataTableColumns<any> = [
  { title: t('common.name'), key: 'name' }, { title: t('common.region'), key: 'region' },
  { title: t('page.pricing.markupMultiplier'), key: 'markup_multiplier', render: row => `${row.markup_multiplier}x` },
  { title: t('page.pricing.fixedShippingFee'), key: 'fixed_shipping_fee', render: row => `$${row.fixed_shipping_fee}` },
  { title: t('common.priority'), key: 'priority' },
  { title: t('common.active'), key: 'is_active', render: row => h(NTag, { type: row.is_active ? 'success' : 'default', size: 'small' }, { default: () => row.is_active ? t('common.active') : t('common.inactive') }) },
  {
    title: t('page.suppliers.actions'), key: 'actions',
    render: row => h(NSpace, { size: 'small' }, {
      default: () => [
        h(NButton, { size: 'small', onClick: () => openRuleModal(row) }, { default: () => t('common.edit') }),
        h(NButton, { size: 'small', type: 'error', onClick: () => deleteRule(row.id) }, { default: () => t('common.delete') }),
      ],
    }),
  },
];

const promoColumns: DataTableColumns<any> = [
  { title: t('common.name'), key: 'name' }, { title: t('common.type'), key: 'type' },
  { title: t('common.regions'), key: 'applicable_regions', render: row => (row.applicable_regions || []).join(', ') },
  { title: t('common.period'), key: 'period', render: row => `${row.start_date ? new Date(row.start_date).toLocaleDateString() : '-'} ~ ${row.end_date ? new Date(row.end_date).toLocaleDateString() : '-'}` },
  { title: t('common.active'), key: 'is_active', render: row => h(NTag, { type: row.is_active ? 'success' : 'default', size: 'small' }, { default: () => row.is_active ? t('common.active') : t('common.inactive') }) },
  {
    title: t('page.suppliers.actions'), key: 'actions',
    render: row => h(NSpace, { size: 'small' }, {
      default: () => [
        h(NButton, { size: 'small', onClick: () => openPromoModal(row) }, { default: () => t('common.edit') }),
        h(NButton, { size: 'small', type: 'error', onClick: () => deletePromo(row.id) }, { default: () => t('common.delete') }),
      ],
    }),
  },
];

async function fetchRules() { const res = await get('/api/admin/v1/pricing/rules'); rules.value = res.data || []; }
async function fetchPromos() { const res = await get('/api/admin/v1/pricing/promotions'); promotions.value = res.data || []; }

function openRuleModal(r?: any) {
  editingRule.value = r || null;
  ruleForm.value = r ? { name: r.name, region: r.region, markup_multiplier: r.markup_multiplier, fixed_shipping_fee: r.fixed_shipping_fee, priority: r.priority, is_active: r.is_active, is_default: r.is_default } : { name: '', region: 'GLOBAL', markup_multiplier: 1.4, fixed_shipping_fee: 5.0, priority: 0, is_active: true, is_default: false };
  modalError.value = ''; showRuleModal.value = true;
}

async function saveRule() {
  modalLoading.value = true;
  try {
    if (editingRule.value) await patch(`/api/admin/v1/pricing/rules/${editingRule.value.id}`, ruleForm.value);
    else await post('/api/admin/v1/pricing/rules', ruleForm.value);
    showRuleModal.value = false; fetchRules();
  } catch (e: any) { modalError.value = e.response?.data?.detail || 'Save failed'; }
  finally { modalLoading.value = false; }
}

async function deleteRule(id: string) { try { await del(`/api/admin/v1/pricing/rules/${id}`); fetchRules(); } catch (e) { console.error(e); } }

function openPromoModal(p?: any) {
  editingPromo.value = p || null;
  promoForm.value = p ? { name: p.name, type: p.type, applicable_regions: p.applicable_regions || [], applicable_categories: p.applicable_categories || [], start_date: p.start_date?.slice(0, 16) || '', end_date: p.end_date?.slice(0, 16) || '', is_active: p.is_active, stackable: p.stackable || false, priority: p.priority || 0 } : { name: '', type: 'COUPON', applicable_regions: [], applicable_categories: [], start_date: '', end_date: '', is_active: true, stackable: false, priority: 0 };
  promoRegions.value = (promoForm.value.applicable_regions || []).join(', ');
  promoCategories.value = (promoForm.value.applicable_categories || []).join(', ');
  modalError.value = ''; showPromoModal.value = true;
}

async function savePromo() {
  modalLoading.value = true;
  try {
    const body = { ...promoForm.value, config: {} };
    if (editingPromo.value) await patch(`/api/admin/v1/pricing/promotions/${editingPromo.value.id}`, body);
    else await post('/api/admin/v1/pricing/promotions', body);
    showPromoModal.value = false; fetchPromos();
  } catch (e: any) { modalError.value = e.response?.data?.detail || 'Save failed'; }
  finally { modalLoading.value = false; }
}

async function deletePromo(id: string) { try { await del(`/api/admin/v1/pricing/promotions/${id}`); fetchPromos(); } catch (e) { console.error(e); } }

async function calculate() {
  calcLoading.value = true;
  try {
    const params: Record<string, any> = { region: calc.value.region, cost_price: calc.value.cost_price };
    if (calc.value.product_id) params.product_id = calc.value.product_id;
    if (calc.value.override_price != null) params.override_price = calc.value.override_price;
    const res = await get('/api/admin/v1/pricing/calculate', { params });
    calcResult.value = res.data;
  } catch (e: any) { calcResult.value = { error: e.response?.data?.detail || 'Calculation failed' }; }
  finally { calcLoading.value = false; }
}

onMounted(() => { fetchRules(); fetchPromos(); });
</script>

<template>
  <div class="flex flex-col gap-4">
    <NTabs v-model:value="tab" type="line">
      <NTabPane name="rules" :tab="$t('page.pricing.pricingRule')">
        <div class="flex flex-col gap-4 pt-2">
          <div class="flex justify-between items-center">
            <span class="text-sm text-[var(--n-text-color-3)]">{{ rules.length }} rule(s)</span>
            <NButton type="primary" size="small" @click="openRuleModal()">{{ $t('page.pricing.addRule') }}</NButton>
          </div>
          <NDataTable :columns="ruleColumns" :data="rules" :bordered="false" size="small" />
        </div>
      </NTabPane>

      <NTabPane name="promotions" :tab="$t('page.pricing.promotions')">
        <div class="flex flex-col gap-4 pt-2">
          <div class="flex justify-between items-center">
            <span class="text-sm text-[var(--n-text-color-3)]">{{ $t('page.pricing.promoCount', { count: promotions.length }) }}</span>
            <NButton type="primary" size="small" @click="openPromoModal()">{{ $t('common.add') }}</NButton>
          </div>
          <NDataTable :columns="promoColumns" :data="promotions" :bordered="false" size="small" />
        </div>
      </NTabPane>

      <NTabPane name="calculator" :tab="$t('page.pricing.priceCalculator')">
        <NCard :title="$t('page.pricing.priceCalculator')" size="small" style="max-width:480px" class="mt-2">
          <div class="flex flex-col gap-3">
            <NFormItem :label="$t('page.pricing.productId')"><NInput v-model:value="calc.product_id" /></NFormItem>
            <NFormItem :label="$t('page.pricing.costPrice')"><NInputNumber v-model:value="calc.cost_price" :min="0" :step="0.01" style="width:100%" /></NFormItem>
            <NFormItem :label="$t('common.region')">
              <NSelect v-model:value="calc.region" :options="regionOpts" />
            </NFormItem>
            <NFormItem :label="$t('page.pricing.overridePrice')"><NInputNumber v-model:value="calc.override_price" :min="0" :step="0.01" style="width:100%" /></NFormItem>
            <NButton type="primary" :loading="calcLoading" @click="calculate">Calculate</NButton>
          </div>
          <div v-if="calcResult" class="mt-4 p-3 bg-[var(--n-color-embedded)] rounded-md text-sm">
            <div v-for="(v, k) in calcResult" :key="k" class="flex justify-between py-1">
              <span class="text-[var(--n-text-color-3)]">{{ k }}</span>
              <span class="font-semibold">{{ typeof v === 'number' ? `$${(v as number).toFixed(2)}` : v }}</span>
            </div>
          </div>
        </NCard>
      </NTabPane>
    </NTabs>

    <!-- Rule Modal -->
    <NModal v-model:show="showRuleModal" preset="card" :title="$t('page.pricing.pricingRule')" style="width:480px">
      <NForm :model="ruleForm" label-placement="left" label-width="140">
        <NFormItem :label="$t('common.name')"><NInput v-model:value="ruleForm.name" /></NFormItem>
        <NFormItem :label="$t('common.region')"><NInput v-model:value="ruleForm.region" /></NFormItem>
        <NFormItem :label="$t('page.pricing.markupMultiplier')"><NInputNumber v-model:value="ruleForm.markup_multiplier" :min="0" :step="0.01" style="width:100%" /></NFormItem>
        <NFormItem :label="$t('page.pricing.fixedShippingFee')"><NInputNumber v-model:value="ruleForm.fixed_shipping_fee" :min="0" :step="0.01" style="width:100%" /></NFormItem>
        <NFormItem :label="$t('common.priority')"><NInputNumber v-model:value="ruleForm.priority" style="width:100%" /></NFormItem>
        <NFormItem :label="$t('common.active')"><NSwitch v-model:value="ruleForm.is_active" /></NFormItem>
        <NFormItem :label="$t('common.default')"><NSwitch v-model:value="ruleForm.is_default" /></NFormItem>
      </NForm>
      <div v-if="modalError" class="text-red-500 text-sm mt-2">{{ modalError }}</div>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showRuleModal = false">{{ $t('common.cancel') }}</NButton>
          <NButton type="primary" :loading="modalLoading" @click="saveRule">{{ $t('common.save') }}</NButton>
        </NSpace>
      </template>
    </NModal>

    <!-- Promo Modal -->
    <NModal v-model:show="showPromoModal" preset="card" :title="$t('page.pricing.promotions')" style="width:480px">
      <NForm :model="promoForm" label-placement="left" label-width="140">
        <NFormItem :label="$t('common.name')"><NInput v-model:value="promoForm.name" /></NFormItem>
        <NFormItem :label="$t('common.type')">
          <NSelect v-model:value="promoForm.type" :options="promoTypeOptions" />
        </NFormItem>
        <NFormItem :label="$t('common.regionsComma')"><NInput v-model:value="promoRegions" @update:value="updatePromoRegions" /></NFormItem>
        <NFormItem :label="$t('common.categoriesComma')"><NInput v-model:value="promoCategories" @update:value="updatePromoCats" /></NFormItem>
        <NFormItem :label="$t('common.start')"><NInput v-model:value="promoForm.start_date" /></NFormItem>
        <NFormItem :label="$t('common.end')"><NInput v-model:value="promoForm.end_date" /></NFormItem>
        <NFormItem :label="$t('common.active')"><NSwitch v-model:value="promoForm.is_active" /></NFormItem>
      </NForm>
      <div v-if="modalError" class="text-red-500 text-sm mt-2">{{ modalError }}</div>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showPromoModal = false">{{ $t('common.cancel') }}</NButton>
          <NButton type="primary" :loading="modalLoading" @click="savePromo">{{ $t('common.save') }}</NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>
