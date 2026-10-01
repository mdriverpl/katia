<script setup>
import { computed, onMounted } from 'vue'
import BrandLogo from './BrandLogo.vue'
import { legalDocuments, legalProfile } from '../legal.js'

const props = defineProps({ documentType: { type: String, required: true } })
const documentContent = computed(() => legalDocuments[props.documentType] || legalDocuments.privacy)
const printDocument = () => window.print()
onMounted(() => {
  document.title = `${documentContent.value.title} · ${legalProfile.appName}`
  const description = document.querySelector('meta[name="description"]')
  if (description) description.content = documentContent.value.introduction
  if (legalProfile.draft) {
    const meta = document.createElement('meta')
    meta.name = 'robots'; meta.content = 'noindex, nofollow'; document.head.appendChild(meta)
  }
})
</script>

<template>
  <main class="legal-page">
    <header class="legal-header">
      <a href="/" class="legal-brand" aria-label="Space & Flow — strona logowania"><BrandLogo /></a>
      <div class="legal-actions"><a href="/">Wróć do aplikacji</a><button type="button" class="text-button" @click="printDocument">Drukuj / zapisz PDF</button></div>
    </header>
    <nav class="legal-tabs" aria-label="Dokumenty aplikacji">
      <a href="/#/privacy" :aria-current="documentType === 'privacy' ? 'page' : undefined">Polityka prywatności</a>
      <a href="/#/terms" :aria-current="documentType === 'terms' ? 'page' : undefined">Warunki korzystania</a>
    </nav>
    <article class="legal-document">
      <h1>{{ documentContent.title }}</h1>
      <p class="legal-meta">Wersja {{ legalProfile.version }} · Data opracowania: {{ legalProfile.updated }}</p>
      <div v-if="legalProfile.draft" class="legal-draft" role="note">
        <strong>Projekt dokumentu — wymaga uzupełnienia przed publikacją jako obowiązujący.</strong>
        <p>Projekt uwzględnia udostępnianie aplikacji innym firmom. Do uzupełnienia pozostają pełna nazwa operatora, kontakt do spraw prywatności, warunki współpracy i powierzenia, okresy przechowywania oraz zasady korzystania z dostawców i przekazywania danych za granicę. Dokument nie potwierdza zgodności faktycznej organizacji przetwarzania z prawem.</p>
      </div>
      <p>{{ documentContent.introduction }}</p>
      <dl class="legal-identity">
        <dt>Operator</dt><dd>{{ legalProfile.operator }}</dd>
        <dt>Adres</dt><dd>{{ legalProfile.address }}</dd>
        <dt>Dane rejestrowe</dt><dd>{{ legalProfile.registration }}</dd>
        <dt>Kontakt roboczy</dt><dd><a :href="`mailto:${legalProfile.email}`">{{ legalProfile.email }}</a></dd>
        <dt>Adres aplikacji</dt><dd><a :href="legalProfile.appUrl">{{ legalProfile.appUrl }}</a></dd>
      </dl>
      <section v-for="section in documentContent.sections" :key="section.id" :aria-labelledby="section.id">
        <h2 :id="section.id">{{ section.title }}</h2>
        <p v-for="paragraph in section.paragraphs || []" :key="paragraph">{{ paragraph }}</p>
        <ul v-if="section.items"><li v-for="item in section.items" :key="item">{{ item }}</li></ul>
        <div v-if="section.table" class="legal-table-wrap" tabindex="0" role="region" :aria-label="section.title">
          <table><thead><tr><th v-for="heading in section.table.headers" :key="heading" scope="col">{{ heading }}</th></tr></thead>
            <tbody><tr v-for="row in section.table.rows" :key="row[0]"><th scope="row">{{ row[0] }}</th><td>{{ row[1] }}</td></tr></tbody>
          </table>
        </div>
        <p v-for="paragraph in section.paragraphsAfter || []" :key="paragraph">{{ paragraph }}</p>
      </section>
      <section aria-labelledby="legal-sources"><h2 id="legal-sources">Podstawy prawne i informacje</h2><ul><li v-for="source in documentContent.sources" :key="source.url"><a :href="source.url" target="_blank" rel="noopener noreferrer">{{ source.label }}</a></li></ul></section>
    </article>
  </main>
</template>

<style scoped>
.legal-page { width: min(1040px, 100%); margin: 0 auto; padding: 28px 24px 64px; color: var(--forest); }
.legal-header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 20px; padding: 12px 0 28px; }
.legal-brand { text-decoration: none; }
.legal-actions, .legal-tabs { display: flex; flex-wrap: wrap; align-items: center; gap: 18px; }
.legal-page a { color: inherit; text-underline-offset: 3px; }
.legal-page a:focus-visible { outline: 3px solid var(--gold); outline-offset: 4px; }
.legal-actions { font-size: 13px; }
.legal-tabs { padding: 18px 0; border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); }
.legal-tabs a[aria-current] { font-weight: 750; }
.legal-document { line-height: 1.75; font-size: 15px; overflow-wrap: anywhere; }
.legal-document h1 { font-size: clamp(28px, 5vw, 40px); line-height: 1.2; margin: 34px 0 12px; }
.legal-document h2 { font-size: 22px; line-height: 1.4; margin: 32px 0 14px; }
.legal-document p { margin: 12px 0; }
.legal-meta { color: var(--muted); font-size: 13px; }
.legal-draft { display: block; width: auto; min-height: 0; padding: 18px 22px; margin: 24px 0; background: #fff3ce; color: #5c4512; border: 1px solid #d8be74; border-radius: 12px; }
.legal-draft p { margin-bottom: 0; font-size: 14px; }
.legal-identity { display: grid; grid-template-columns: 150px 1fr; gap: 12px 20px; padding: 22px 0; margin: 22px 0; border-block: 1px solid var(--line); }
.legal-identity dt { font-weight: 650; }
.legal-identity dd { margin: 0; }
.legal-document ul { padding-left: 24px; }
.legal-document li { margin: 10px 0; }
.legal-table-wrap { overflow-x: auto; margin: 18px 0; }
.legal-document table { width: 100%; min-width: 540px; border-collapse: collapse; font-size: 14px; }
.legal-document th, .legal-document td { padding: 14px; border: 1px solid var(--line); vertical-align: top; text-align: left; white-space: normal; }
.legal-document th { font-weight: 650; }
.legal-document tbody th { width: 31%; }
@media (max-width: 600px) { .legal-page { padding: 18px 16px 40px; } .legal-identity { grid-template-columns: 1fr; gap: 4px; } .legal-identity dd { margin-bottom: 12px; } }
@media print {
  .legal-page { width: 100%; padding: 0; color: #000; background: #fff; }
  .legal-actions, .legal-tabs { display: none; }
  .legal-header { padding: 0; }
  .legal-document { font-size: 10pt; line-height: 1.45; }
  .legal-document h1 { font-size: 22pt; }
  .legal-document h2 { font-size: 14pt; break-after: avoid; }
  .legal-table-wrap { overflow: visible; }
  .legal-document table { min-width: 0; font-size: 9pt; }
  .legal-document tr { break-inside: avoid; }
  .legal-document a { text-decoration: none; }
  .legal-draft { color: #000; border-color: #000; }
}
</style>
