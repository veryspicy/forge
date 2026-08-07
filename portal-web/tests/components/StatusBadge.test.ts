import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import StatusBadge from "~/components/admin/StatusBadge.vue";

describe("StatusBadge", () => {
  it("renders pending_payment status (amber)", () => {
    const wrapper = mount(StatusBadge, {
      props: { status: "pending_payment" },
    });
    expect(wrapper.text()).toContain("待支付");
  });

  it("renders paid status (blue)", () => {
    const wrapper = mount(StatusBadge, {
      props: { status: "paid" },
    });
    expect(wrapper.text()).toContain("已支付");
  });

  it("renders procuring status (indigo)", () => {
    const wrapper = mount(StatusBadge, {
      props: { status: "procuring" },
    });
    expect(wrapper.text()).toContain("采购中");
  });

  it("renders shipped status (teal)", () => {
    const wrapper = mount(StatusBadge, {
      props: { status: "shipped" },
    });
    expect(wrapper.text()).toContain("已发货");
  });

  it("renders in_transit status (cyan)", () => {
    const wrapper = mount(StatusBadge, {
      props: { status: "in_transit" },
    });
    expect(wrapper.text()).toContain("运输中");
  });

  it("renders delivered status (green)", () => {
    const wrapper = mount(StatusBadge, {
      props: { status: "delivered" },
    });
    expect(wrapper.text()).toContain("已送达");
  });

  it("renders completed status (slate)", () => {
    const wrapper = mount(StatusBadge, {
      props: { status: "completed" },
    });
    expect(wrapper.text()).toContain("已完成");
  });

  it("renders procurement_failed status (red)", () => {
    const wrapper = mount(StatusBadge, {
      props: { status: "procurement_failed" },
    });
    expect(wrapper.text()).toContain("采购异常");
  });

  it("renders unknown status gracefully", () => {
    const wrapper = mount(StatusBadge, {
      props: { status: "some_unknown_status" },
    });
    // Falls back to raw status text
    expect(wrapper.text()).toContain("some_unknown_status");
  });
});
