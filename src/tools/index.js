/**
 * tools/index.js — 本插件提供的工具清单。
 *
 * 一个工具一个文件（spec 与 execute 放在一起），因为宿主管参数的方式是
 * **按 schema 过滤**：schema 没声明的参数会被静默丢掉。所以「读了哪些 args」
 * 必须和「声明了哪些」在同一处能对上，摊在一个大文件里就看不出来了。
 *
 * 返回 spec 是函数而不是常量：每次注册都拿到新对象，避免宿主改动污染下次注册。
 */
import * as check from './check.js';
import * as figure from './figure.js';
import * as pdf from './pdf.js';

export function toolDefinitions() {
  return [
    { spec: pdf.spec, execute: pdf.execute },
    { spec: figure.spec, execute: figure.execute },
    { spec: check.spec, execute: check.execute },
  ];
}
