import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import StatCard from "~/components/admin/StatCard.vue";

describe("StatCard", () => {
  it("renders title and value", () => {
    const wrapper = mount(StatCard, {
      props: { title: "今日订单数", value: "128" },
    });

    expect(wrapper.text()).toContain("今日订单数");
    expect(wrapper.text()).toContain("128");
  });

  it("renders up trend arrow", () => {
    const wrapper = mount(StatCard, {
      props: {
        title: "Revenue",
        value: "$5,000",
        trend: "up",
        trendValue: "+12.5%",
      },
    });

    expect(wrapper.text()).toContain("+12.5%");
    // up trend should have text-success class
    const trendContainer = wrapper.find(".text-success");
    expect(trendContainer.exists()).toBe(true);
  });

  it("renders down trend arrow", () => {
    const wrapper = mount(StatCard, {
      props: {
        title: "Revenue",
        value: "$3,200",
        trend: "down",
        trendValue: "-5.2%",
      },
    });

    expect(wrapper.text()).toContain("-5.2%");
    const trendContainer = wrapper.find(".text-error");
    expect(trendContainer.exists()).toBe(true);
  });

  it("renders neutral trend", () => {
    const wrapper = mount(StatCard, {
      props: {
        title: "Revenue",
        value: "$4,000",
        trend: "neutral",
        trendValue: "0%",
      },
    });

    expect(wrapper.text()).toContain("0%");
    const trendContainer = wrapper.find(".text-neutral-400");
    expect(trendContainer.exists()).toBe(true);
  });

  it("renders without trend", () => {
    const wrapper = mount(StatCard, {
      props: {
        title: "Suppliers",
        value: "42",
      },
    });

    expect(wrapper.text()).toContain("Suppliers");
    expect(wrapper.text()).toContain("42");
    // No trend section should be rendered
    const svg = wrapper.find("svg");
    expect(svg.exists()).toBe(false);
  });
});
