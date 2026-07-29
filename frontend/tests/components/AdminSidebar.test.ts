import { describe, it, expect } from "vitest";
import { mount, RouterLinkStub } from "@vue/test-utils";
import AdminSidebar from "~/components/admin/AdminSidebar.vue";

describe("AdminSidebar", () => {
  it("renders all 7 menu items", () => {
    const wrapper = mount(AdminSidebar, {
      props: { collapsed: false },
      global: {
        stubs: {
          NuxtLink: RouterLinkStub,
        },
      },
    });

    const links = wrapper.findAllComponents(RouterLinkStub);
    expect(links.length).toBe(7);
  });

  it("highlights active route", () => {
    const wrapper = mount(AdminSidebar, {
      props: { collapsed: false },
      global: {
        stubs: {
          NuxtLink: RouterLinkStub,
        },
      },
    });

    const links = wrapper.findAllComponents(RouterLinkStub);
    const dashboardLink = links.find((l) => l.props("to") === "/admin");
    expect(dashboardLink).toBeTruthy();
    expect(dashboardLink!.props("to")).toBe("/admin");
  });

  it("toggles collapse via emit", async () => {
    const wrapper = mount(AdminSidebar, {
      props: { collapsed: false },
      global: {
        stubs: {
          NuxtLink: true,
        },
      },
    });

    const toggleBtn = wrapper.find("button");
    expect(toggleBtn.exists()).toBe(true);

    await toggleBtn.trigger("click");
    expect(wrapper.emitted("toggle")).toBeTruthy();
    expect(wrapper.emitted("toggle")!.length).toBe(1);
  });

  it("applies collapsed class when collapsed prop is true", () => {
    const wrapper = mount(AdminSidebar, {
      props: { collapsed: true },
      global: {
        stubs: {
          NuxtLink: true,
        },
      },
    });

    const aside = wrapper.find("aside");
    expect(aside.classes()).toContain("w-16");
  });

  it("applies expanded class when collapsed prop is false", () => {
    const wrapper = mount(AdminSidebar, {
      props: { collapsed: false },
      global: {
        stubs: {
          NuxtLink: true,
        },
      },
    });

    const aside = wrapper.find("aside");
    expect(aside.classes()).toContain("w-60");
  });

  it("shows short logo when collapsed", () => {
    const wrapper = mount(AdminSidebar, {
      props: { collapsed: true },
      global: { stubs: { NuxtLink: true } },
    });

    expect(wrapper.text()).toContain("PA");
  });

  it("shows full logo when expanded", () => {
    const wrapper = mount(AdminSidebar, {
      props: { collapsed: false },
      global: { stubs: { NuxtLink: true } },
    });

    expect(wrapper.text()).toContain("Forge Admin");
  });
});
