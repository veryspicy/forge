import { describe, it, expect, vi } from "vitest";
import { mount } from "@vue/test-utils";
import DataTable from "~/components/admin/DataTable.vue";

const mockColumns = [
  { key: "id", label: "ID", sortable: true },
  { key: "name", label: "名称", sortable: false },
  { key: "price", label: "价格", sortable: true, align: "right" as const },
];

const mockData = [
  { id: "1", name: "Product A", price: 99 },
  { id: "2", name: "Product B", price: 199 },
];

describe("DataTable", () => {
  it("renders columns from props", () => {
    const wrapper = mount(DataTable, {
      props: { columns: mockColumns, data: mockData },
    });

    const headers = wrapper.findAll("th");
    // 3 columns + possibly a checkbox column
    const headerTexts = headers.map((h) => h.text());
    expect(headerTexts).toContain("ID");
    expect(headerTexts).toContain("名称");
    expect(headerTexts).toContain("价格");
  });

  it("renders data rows", () => {
    const wrapper = mount(DataTable, {
      props: { columns: mockColumns, data: mockData },
    });

    const rows = wrapper.findAll("tbody tr");
    expect(rows.length).toBe(2);
    expect(wrapper.text()).toContain("Product A");
    expect(wrapper.text()).toContain("Product B");
  });

  it("checkbox selection emits update:selected event", async () => {
    const wrapper = mount(DataTable, {
      props: {
        columns: mockColumns,
        data: mockData,
        selectable: true,
        selected: [],
      },
    });

    const checkboxes = wrapper.findAll('input[type="checkbox"]');
    // First checkbox is "select all", subsequent are row checkboxes
    const rowCheckbox = checkboxes[1];
    expect(rowCheckbox.exists()).toBe(true);

    await rowCheckbox.setValue(true);
    const emitted = wrapper.emitted("update:selected");
    expect(emitted).toBeTruthy();
  });

  it("sort column click emits sort event", async () => {
    const wrapper = mount(DataTable, {
      props: { columns: mockColumns, data: mockData },
    });

    const sortableHeader = wrapper.findAll("th").find((h) => h.text().includes("ID"));
    expect(sortableHeader).toBeTruthy();

    await sortableHeader!.trigger("click");
    const sortEvents = wrapper.emitted("sort");
    expect(sortEvents).toBeTruthy();
    expect(sortEvents![0]).toEqual(["id", "asc"]);
  });

  it("loading state shows skeleton", () => {
    const wrapper = mount(DataTable, {
      props: { columns: mockColumns, data: [], loading: true },
    });

    const skeletonDivs = wrapper.findAll(".animate-pulse");
    expect(skeletonDivs.length).toBeGreaterThan(0);
  });

  it("empty state message", () => {
    const wrapper = mount(DataTable, {
      props: { columns: mockColumns, data: [] },
    });

    expect(wrapper.text()).toContain("暂无数据");
  });

  it("pagination controls", () => {
    const wrapper = mount(DataTable, {
      props: {
        columns: mockColumns,
        data: mockData,
        currentPage: 1,
        totalPages: 5,
      },
    });

    expect(wrapper.text()).toContain("1 / 5 页");
    expect(wrapper.text()).toContain("上一页");
    expect(wrapper.text()).toContain("下一页");
  });

  it("emits page-change on next page click", async () => {
    const wrapper = mount(DataTable, {
      props: {
        columns: mockColumns,
        data: mockData,
        currentPage: 1,
        totalPages: 5,
      },
    });

    const nextBtn = wrapper.find("button:not([disabled])");
    const buttons = wrapper.findAll("button");
    const nextPageBtn = buttons.find((b) => b.text().includes("下一页"));
    expect(nextPageBtn).toBeTruthy();

    await nextPageBtn!.trigger("click");
    expect(wrapper.emitted("page-change")).toBeTruthy();
    expect(wrapper.emitted("page-change")![0]).toEqual([2]);
  });
});
