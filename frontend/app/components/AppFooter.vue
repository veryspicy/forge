<template>
  <footer class="bg-neutral-900 text-neutral-300">
    <div class="max-w-7xl mx-auto px-4 py-12">
      <!-- Main Grid -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-8">
        <!-- Shop -->
        <div>
          <h4 class="text-sm font-heading font-semibold text-neutral-100 uppercase tracking-wider mb-4">
            {{ $t('footer.shop') }}
          </h4>
          <ul class="space-y-2.5">
            <li>
              <NuxtLink to="/products?category=pet-food" class="text-sm text-neutral-400 hover:text-neutral-100 transition-colors">
                {{ $t('footer.petFood') }}
              </NuxtLink>
            </li>
            <li>
              <NuxtLink to="/products?category=toys" class="text-sm text-neutral-400 hover:text-neutral-100 transition-colors">
                {{ $t('footer.toys') }}
              </NuxtLink>
            </li>
            <li>
              <NuxtLink to="/products?category=health-wellness" class="text-sm text-neutral-400 hover:text-neutral-100 transition-colors">
                {{ $t('footer.healthWellness') }}
              </NuxtLink>
            </li>
            <li>
              <NuxtLink to="/products?category=accessories" class="text-sm text-neutral-400 hover:text-neutral-100 transition-colors">
                {{ $t('footer.accessories') }}
              </NuxtLink>
            </li>
            <li>
              <NuxtLink to="/products?category=grooming" class="text-sm text-neutral-400 hover:text-neutral-100 transition-colors">
                {{ $t('footer.grooming') }}
              </NuxtLink>
            </li>
          </ul>
        </div>

        <!-- Support -->
        <div>
          <h4 class="text-sm font-heading font-semibold text-neutral-100 uppercase tracking-wider mb-4">
            {{ $t('footer.support') }}
          </h4>
          <ul class="space-y-2.5">
            <li>
              <NuxtLink to="/faqs" class="text-sm text-neutral-400 hover:text-neutral-100 transition-colors">
                {{ $t('footer.faqs') }}
              </NuxtLink>
            </li>
            <li>
              <NuxtLink to="/shipping" class="text-sm text-neutral-400 hover:text-neutral-100 transition-colors">
                {{ $t('footer.shippingInfo') }}
              </NuxtLink>
            </li>
            <li>
              <NuxtLink to="/returns" class="text-sm text-neutral-400 hover:text-neutral-100 transition-colors">
                {{ $t('footer.returns') }}
              </NuxtLink>
            </li>
            <li>
              <NuxtLink to="/contact" class="text-sm text-neutral-400 hover:text-neutral-100 transition-colors">
                {{ $t('footer.contactUs') }}
              </NuxtLink>
            </li>
          </ul>
        </div>

        <!-- About -->
        <div>
          <h4 class="text-sm font-heading font-semibold text-neutral-100 uppercase tracking-wider mb-4">
            {{ $t('footer.about') }}
          </h4>
          <ul class="space-y-2.5">
            <li>
              <NuxtLink to="/story" class="text-sm text-neutral-400 hover:text-neutral-100 transition-colors">
                {{ $t('footer.ourStory') }}
              </NuxtLink>
            </li>
            <li>
              <NuxtLink to="/sustainability" class="text-sm text-neutral-400 hover:text-neutral-100 transition-colors">
                {{ $t('footer.sustainability') }}
              </NuxtLink>
            </li>
            <li>
              <NuxtLink to="/blog" class="text-sm text-neutral-400 hover:text-neutral-100 transition-colors">
                {{ $t('footer.blog') }}
              </NuxtLink>
            </li>
            <li>
              <NuxtLink to="/careers" class="text-sm text-neutral-400 hover:text-neutral-100 transition-colors">
                {{ $t('footer.careers') }}
              </NuxtLink>
            </li>
          </ul>
        </div>

        <!-- Legal -->
        <div>
          <h4 class="text-sm font-heading font-semibold text-neutral-100 uppercase tracking-wider mb-4">
            {{ $t('footer.legal') }}
          </h4>
          <ul class="space-y-2.5">
            <li>
              <NuxtLink to="/privacy" class="text-sm text-neutral-400 hover:text-neutral-100 transition-colors">
                {{ $t('footer.privacyPolicy') }}
              </NuxtLink>
            </li>
            <li>
              <NuxtLink to="/terms" class="text-sm text-neutral-400 hover:text-neutral-100 transition-colors">
                {{ $t('footer.termsOfService') }}
              </NuxtLink>
            </li>
            <li>
              <NuxtLink to="/cookies" class="text-sm text-neutral-400 hover:text-neutral-100 transition-colors">
                {{ $t('footer.cookies') }}
              </NuxtLink>
            </li>
          </ul>
        </div>
      </div>

      <!-- Newsletter -->
      <div class="mt-12 flex flex-col sm:flex-row items-start sm:items-center gap-4 p-6 rounded-2xl bg-neutral-800/50">
        <div class="flex-shrink-0">
          <h4 class="text-base font-heading font-semibold text-neutral-100">
            {{ $t('footer.stayInLoop') }}
          </h4>
          <p class="text-sm text-neutral-400 mt-0.5">
            {{ $t('footer.newsletterHint') }}
          </p>
        </div>
        <form class="flex flex-1 w-full gap-2" @submit.prevent="onSubscribe">
          <input
            v-model="email"
            type="email"
            required
            :placeholder="$t('footer.enterEmail')"
            class="flex-1 text-sm bg-neutral-800 border border-neutral-700 rounded-lg px-4 py-2.5 text-neutral-200 placeholder-neutral-500 focus:outline-none focus:border-primary-500 transition-colors"
          />
          <button
            type="submit"
            class="flex-shrink-0 bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium px-5 py-2.5 rounded-lg transition-colors"
          >
            {{ $t('footer.subscribe') }}
          </button>
        </form>
      </div>

      <!-- Divider -->
      <div class="border-t border-neutral-800 my-8" />

      <!-- Bottom Bar -->
      <div class="flex flex-col sm:flex-row items-center justify-between gap-3">
        <p class="text-sm text-neutral-500">
          {{ $t('footer.copyright') }}
        </p>
        <p class="text-sm text-neutral-500">
          {{ $t('footer.paymentMethods') }}
        </p>
      </div>
    </div>
  </footer>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const email = ref('')

function onSubscribe() {
  // Placeholder: subscription logic will be wired later
  email.value = ''
}
</script>
