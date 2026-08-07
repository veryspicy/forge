import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import ChatStatusBadge from "~/components/admin/ChatStatusBadge.vue";

describe("ChatStatusBadge", () => {
  it("renders waiting status", () => {
    const wrapper = mount(ChatStatusBadge, {
      props: { status: "waiting" },
    });
    expect(wrapper.text()).toContain("等待中");
  });

  it("renders ai_processing status", () => {
    const wrapper = mount(ChatStatusBadge, {
      props: { status: "ai_processing" },
    });
    expect(wrapper.text()).toContain("AI处理中");
  });

  it("renders pending_takeover status", () => {
    const wrapper = mount(ChatStatusBadge, {
      props: { status: "pending_takeover" },
    });
    expect(wrapper.text()).toContain("待人工接管");
  });

  it("renders human_processing status", () => {
    const wrapper = mount(ChatStatusBadge, {
      props: { status: "human_processing" },
    });
    expect(wrapper.text()).toContain("人工处理中");
  });

  it("renders resolved status", () => {
    const wrapper = mount(ChatStatusBadge, {
      props: { status: "resolved" },
    });
    expect(wrapper.text()).toContain("已解决");
  });
});
