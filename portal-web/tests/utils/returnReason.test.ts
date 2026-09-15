import { describe, it, expect } from "vitest";
import {
  RETURN_REASON_CODES,
  normalizeReturnReasonCode,
  returnReasonI18nKey,
  returnReasonLabel,
} from "~/utils/returnReason";

/** 模拟 vue-i18n 的 t()，只回显 key，便于断言本地化键选择是否正确 */
const fakeT = (key: string) => `t:${key}`;

describe("returnReason 字典", () => {
  it("字典覆盖 5 个标准 code", () => {
    expect([...RETURN_REASON_CODES]).toEqual([
      "damaged",
      "wrongItem",
      "notAsDescribed",
      "noLongerNeeded",
      "other",
    ]);
  });

  it("标准 code 归一化后保持原值", () => {
    expect(normalizeReturnReasonCode("damaged")).toBe("damaged");
    expect(normalizeReturnReasonCode("wrongItem")).toBe("wrongItem");
  });

  it("历史英文文案（大小写/首尾空格）可映射回 code", () => {
    expect(normalizeReturnReasonCode("Damaged or defective")).toBe("damaged");
    expect(normalizeReturnReasonCode("  WRONG ITEM RECEIVED ")).toBe("wrongItem");
    expect(normalizeReturnReasonCode("Not as described")).toBe("notAsDescribed");
    expect(normalizeReturnReasonCode("No longer needed")).toBe("noLongerNeeded");
  });

  it("other 无历史英文对应时按运营手填处理", () => {
    expect(normalizeReturnReasonCode("other")).toBe("other");
    expect(normalizeReturnReasonCode("Other")).toBeNull();
  });

  it("无法识别的运营手填内容不误映射", () => {
    expect(normalizeReturnReasonCode("客户电话沟通后同意退货")).toBeNull();
    expect(normalizeReturnReasonCode("")).toBeNull();
    expect(normalizeReturnReasonCode(null)).toBeNull();
    expect(normalizeReturnReasonCode(undefined)).toBeNull();
  });

  it("i18n key 按 code 生成，未知内容返回 null", () => {
    expect(returnReasonI18nKey("damaged")).toBe("returns.reasonDamaged");
    expect(returnReasonI18nKey("Not as described")).toBe("returns.reasonNotAsDescribed");
    expect(returnReasonI18nKey("自由文本")).toBeNull();
  });

  it("label 走当前语言本地化", () => {
    expect(returnReasonLabel("wrongItem", fakeT)).toBe("t:returns.reasonWrongItem");
    expect(returnReasonLabel("Damaged or defective", fakeT)).toBe("t:returns.reasonDamaged");
  });

  it("label 对空值给占位符、对未知内容原样回显（不丢信息）", () => {
    expect(returnReasonLabel("", fakeT)).toBe("-");
    expect(returnReasonLabel(null, fakeT)).toBe("-");
    expect(returnReasonLabel("运营手填原因", fakeT)).toBe("运营手填原因");
  });
});
