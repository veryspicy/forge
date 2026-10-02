import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import { createI18n } from "vue-i18n";
import OrderStatusBadge from "~/components/OrderStatusBadge.vue";

// 单测不加载 nuxt i18n 模块，注入最小可用字典（命名空间与 orders.* 对齐）
const ordersMessages = {
  pending: "待付款",
  confirmed: "已付款·待审核",
  paid: "已付款",
  processing: "处理中",
  shipped: "已发货",
  delivered: "已确认收货",
  completed: "已完成",
  cancelled: "已取消",
  refunded: "已退款",
  partiallyRefunded: "部分退款",
};

const i18n = createI18n({
  legacy: false,
  locale: "zh",
  messages: {
    en: { orders: ordersMessages },
    zh: { orders: ordersMessages },
    ar: { orders: ordersMessages },
    de: { orders: ordersMessages },
    fr: { orders: ordersMessages },
  },
});

const mountBadge = (props: { status: string; paymentStatus?: string | null }) =>
  mount(OrderStatusBadge, { props, global: { plugins: [i18n] } });

// 根元素为 span，内部每个状态徽标各为一个 span
const badgeCount = (wrapper: ReturnType<typeof mountBadge>) =>
  wrapper.findAll("span > span").length;

describe("OrderStatusBadge", () => {
  it("renders only the fulfillment badge when payment is paid", () => {
    const wrapper = mountBadge({ status: "shipped", paymentStatus: "paid" });
    expect(badgeCount(wrapper)).toBe(1);
    expect(wrapper.text()).toContain("已发货");
    expect(wrapper.html()).toContain("bg-purple-100");
  });

  it("appends an orange partial-refund badge for partially_refunded payment", () => {
    const wrapper = mountBadge({
      status: "shipped",
      paymentStatus: "partially_refunded",
    });
    expect(badgeCount(wrapper)).toBe(2);
    expect(wrapper.text()).toContain("已发货");
    expect(wrapper.text()).toContain("部分退款");
    expect(wrapper.html()).toContain("bg-orange-100");
  });

  it("appends a red refund badge for refunded payment", () => {
    const wrapper = mountBadge({ status: "cancelled", paymentStatus: "refunded" });
    expect(badgeCount(wrapper)).toBe(2);
    expect(wrapper.text()).toContain("已取消");
    expect(wrapper.text()).toContain("已退款");
    expect(wrapper.html()).toContain("bg-red-100");
  });

  it("does not duplicate the badge when fulfillment status is already refunded", () => {
    const wrapper = mountBadge({ status: "refunded", paymentStatus: "refunded" });
    expect(badgeCount(wrapper)).toBe(1);
    expect(wrapper.text()).toContain("已退款");
  });

  it("ignores non-refund payment statuses", () => {
    const wrapper = mountBadge({ status: "delivered", paymentStatus: "unpaid" });
    expect(badgeCount(wrapper)).toBe(1);
    expect(wrapper.text()).toContain("已确认收货");
    expect(wrapper.html()).toContain("bg-green-100");
  });
});
