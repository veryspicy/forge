<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { createReusableTemplate } from '@vueuse/core';
import { NGrid, NGi, NCard, NSpin } from 'naive-ui';
import { useAppStore } from '@/store/modules/app';
import { useThemeStore } from '@/store/modules/theme';
import { useEcharts } from '@/hooks/common/echarts';
import { get } from '@/service/api/helper';

// ==================== Stores ====================
const appStore = useAppStore();
const themeStore = useThemeStore();

// ==================== State ====================
const loading = ref(true);
const stats = ref<Record<string, any>>({});
const orderTrend = ref<{ dates: string[]; counts: number[] }>({ dates: [], counts: [] });
const categoryData = ref<{ name: string; value: number }[]>([]);

// ==================== API Calls ====================
async function fetchDashboard() {
  const res = await get('/api/admin/v1/dashboard');
  stats.value = res.data;
}

async function fetchOrdersTrend() {
  try {
    const res = await get('/api/admin/v1/orders', { page: 1, page_size: 100 });
    const orders = res.data?.list || res.data?.data || res.data || [];
    const arr: any[] = Array.isArray(orders) ? orders : [];

    const now = new Date();
    const dayMap: Record<string, number> = {};
    const last7Days: string[] = [];
    for (let i = 6; i >= 0; i--) {
      const d = new Date(now);
      d.setDate(d.getDate() - i);
      const key = `${d.getMonth() + 1}/${d.getDate()}`;
      last7Days.push(key);
      dayMap[key] = 0;
    }

    arr.forEach((o: any) => {
      const dateStr = o.created_at || o.create_time || o.order_time;
      if (dateStr) {
        const d = new Date(dateStr);
        const key = `${d.getMonth() + 1}/${d.getDate()}`;
        if (key in dayMap) dayMap[key]++;
      }
    });

    orderTrend.value = {
      dates: last7Days,
      counts: last7Days.map(k => dayMap[k])
    };
  } catch {
    orderTrend.value = { dates: [], counts: [] };
  }
}

async function fetchProductCategories() {
  try {
    const res = await get('/api/admin/v1/products', { page: 1, page_size: 100 });
    const products = res.data?.list || res.data?.data || res.data || [];
    const arr: any[] = Array.isArray(products) ? products : [];

    const catMap: Record<string, number> = {};
    arr.forEach((p: any) => {
      const cat = p.category || 'Uncategorized';
      catMap[cat] = (catMap[cat] || 0) + 1;
    });

    const entries = Object.entries(catMap).sort((a, b) => b[1] - a[1]);
    const top5 = entries.slice(0, 5);
    const others = entries.slice(5);
    const result = top5.map(([name, value]) => ({ name, value }));
    if (others.length > 0) {
      result.push({ name: 'Others', value: others.reduce((sum, [, v]) => sum + v, 0) });
    }

    categoryData.value = result;
  } catch {
    categoryData.value = [];
  }
}

onMounted(async () => {
  try {
    await Promise.all([fetchDashboard(), fetchOrdersTrend(), fetchProductCategories()]);
  } catch (e) {
    console.error('Dashboard load failed', e);
  } finally {
    loading.value = false;
  }
});

// ==================== Stat Cards ====================
interface StatCard {
  key: string;
  title: string;
  value: string;
  numericValue: number;
  prefix: string;
  suffix: string;
  decimals: number;
  icon: string;
  color: { start: string; end: string };
}

const colorSchemes = [
  { start: '#ec4786', end: '#b955a4' },
  { start: '#865ec0', end: '#5144b4' },
  { start: '#56cdf3', end: '#719de3' },
  { start: '#fcbc25', end: '#f68057' }
];

const statCards = computed<StatCard[]>(() => {
  const n = (v: any) => Number(v);
  const has = (v: any) => v != null;

  return [
    {
      key: 'today_orders',
      title: 'page.dashboard.todayOrders',
      value: String(stats.value.today_orders ?? '-'),
      numericValue: n(stats.value.today_orders),
      prefix: '',
      suffix: '',
      decimals: 0,
      icon: 'ant-design:shopping-cart-outlined',
      color: colorSchemes[0]
    },
    {
      key: 'pending_orders',
      title: 'page.dashboard.pendingOrders',
      value: String(stats.value.pending_orders ?? '-'),
      numericValue: n(stats.value.pending_orders),
      prefix: '',
      suffix: '',
      decimals: 0,
      icon: 'ant-design:clock-circle-outlined',
      color: colorSchemes[1]
    },
    {
      key: 'today_gmv',
      title: 'page.dashboard.todayGMV',
      value: has(stats.value.today_gmv) ? `$${Number(stats.value.today_gmv).toFixed(2)}` : '-',
      numericValue: n(stats.value.today_gmv),
      prefix: '$',
      suffix: '',
      decimals: 2,
      icon: 'ant-design:dollar-outlined',
      color: colorSchemes[2]
    },
    {
      key: 'active_products',
      title: 'page.dashboard.activeProducts',
      value: String(stats.value.active_products ?? '-'),
      numericValue: n(stats.value.active_products),
      prefix: '',
      suffix: '',
      decimals: 0,
      icon: 'ant-design:appstore-outlined',
      color: colorSchemes[3]
    },
    {
      key: 'probe_adoption_rate',
      title: 'page.dashboard.probeAdoption',
      value: has(stats.value.probe_adoption_rate) ? `${stats.value.probe_adoption_rate}%` : '-',
      numericValue: n(stats.value.probe_adoption_rate),
      prefix: '',
      suffix: '%',
      decimals: 0,
      icon: 'ant-design:percentage-outlined',
      color: colorSchemes[0]
    },
    {
      key: 'procurement_errors',
      title: 'page.dashboard.procurementErrors',
      value: String(stats.value.procurement_errors ?? '-'),
      numericValue: n(stats.value.procurement_errors),
      prefix: '',
      suffix: '',
      decimals: 0,
      icon: 'ant-design:warning-outlined',
      color: colorSchemes[1]
    },
    {
      key: 'total_suppliers',
      title: 'page.dashboard.activeSuppliers',
      value: String(stats.value.total_suppliers ?? '-'),
      numericValue: n(stats.value.total_suppliers),
      prefix: '',
      suffix: '',
      decimals: 0,
      icon: 'ant-design:team-outlined',
      color: colorSchemes[2]
    },
    {
      key: 'today_probe_requests',
      title: 'page.dashboard.probeRequests',
      value: String(stats.value.today_probe_requests ?? '-'),
      numericValue: n(stats.value.today_probe_requests),
      prefix: '',
      suffix: '',
      decimals: 0,
      icon: 'ant-design:scan-outlined',
      color: colorSchemes[3]
    }
  ];
});

const statRows = computed(() => [statCards.value.slice(0, 4), statCards.value.slice(4, 8)]);

// ==================== GradientBg reusable template ====================
interface GradientBgProps {
  gradientColor: string;
}
const [DefineGradientBg, GradientBg] = createReusableTemplate<GradientBgProps>();

function getGradientColor(color: StatCard['color']) {
  return `linear-gradient(to bottom right, ${color.start}, ${color.end})`;
}

// ==================== Line Chart (Orders Trend) ====================
const { domRef: lineDomRef, updateOptions: updateLineOptions } = useEcharts(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: '3%', right: '4%', bottom: '3%', top: '10%' },
  xAxis: { type: 'category', boundaryGap: false, data: [] as string[] },
  yAxis: { type: 'value', minInterval: 1 },
  series: [
    {
      color: '#8e9dff',
      name: 'Orders',
      type: 'line',
      smooth: true,
      areaStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0.25, color: '#8e9dff' },
            { offset: 1, color: '#fff' }
          ]
        }
      },
      data: [] as number[]
    }
  ]
}));

function updateLineChart() {
  updateLineOptions(opts => {
    opts.xAxis.data = orderTrend.value.dates;
    opts.series[0].data = orderTrend.value.counts;
    return opts;
  });
}

watch(orderTrend, () => updateLineChart(), { deep: true });

// ==================== Pie Chart (Product Categories) ====================
const { domRef: pieDomRef, updateOptions: updatePieOptions } = useEcharts(() => ({
  tooltip: { trigger: 'item' },
  legend: { bottom: '1%', left: 'center', itemStyle: { borderWidth: 0 } },
  series: [
    {
      color: ['#5da8ff', '#8e9dff', '#fedc69', '#26deca', '#ec4786', '#fcbc25'],
      name: 'Categories',
      type: 'pie',
      radius: ['45%', '75%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 1 },
      label: { show: false, position: 'center' },
      emphasis: { label: { show: true, fontSize: '12' } },
      labelLine: { show: false },
      data: [] as { name: string; value: number }[]
    }
  ]
}));

function updatePieChart() {
  updatePieOptions(opts => {
    opts.series[0].data = categoryData.value;
    return opts;
  });
}

watch(categoryData, () => updatePieChart(), { deep: true });

// ==================== Locale watch ====================
watch(
  () => appStore.locale,
  () => {
    updateLineChart();
    updatePieChart();
  }
);
</script>

<template>
  <NSpin :show="loading">
    <NSpace vertical :size="16">
      <!-- Define GradientBg reusable template -->
      <DefineGradientBg v-slot="{ $slots, gradientColor }">
        <div
          class="px-16px pb-4px pt-8px text-white"
          :style="{ backgroundImage: gradientColor, borderRadius: themeStore.themeRadius + 'px' }"
        >
          <component :is="$slots.default" />
        </div>
      </DefineGradientBg>

      <!-- Stat Cards: 2 rows x 4 columns -->
      <div v-for="(row, rowIdx) in statRows" :key="rowIdx">
        <NGrid cols="s:1 m:2 l:4" responsive="screen" :x-gap="16" :y-gap="16">
          <NGi v-for="item in row" :key="item.key">
            <GradientBg :gradient-color="getGradientColor(item.color)" class="flex-1">
              <h3 class="text-16px">{{ $t(item.title) }}</h3>
              <div class="flex justify-between pt-12px">
                <SvgIcon :icon="item.icon" class="text-32px" />
                <span class="text-30px font-bold">
                  <template v-if="Number.isNaN(item.numericValue)">{{ item.value }}</template>
                  <CountTo
                    v-else
                    :start-value="0"
                    :end-value="item.numericValue"
                    :decimals="item.decimals"
                    :prefix="item.prefix"
                    :suffix="item.suffix"
                  />
                </span>
              </div>
            </GradientBg>
          </NGi>
        </NGrid>
      </div>

      <!-- Charts Row -->
      <NGrid :x-gap="16" :y-gap="16" responsive="screen" item-responsive>
        <NGi span="24 s:24 m:14">
          <NCard :bordered="false" :title="$t('page.dashboard.ordersTrend')" size="small" class="card-wrapper">
            <div ref="lineDomRef" class="h-360px overflow-hidden"></div>
          </NCard>
        </NGi>
        <NGi span="24 s:24 m:10">
          <NCard :bordered="false" :title="$t('page.dashboard.productCategories')" size="small" class="card-wrapper">
            <div ref="pieDomRef" class="h-360px overflow-hidden"></div>
          </NCard>
        </NGi>
      </NGrid>
    </NSpace>
  </NSpin>
</template>

<style scoped>
.card-wrapper {
  height: 100%;
}
</style>
