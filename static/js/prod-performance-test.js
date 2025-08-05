// Production Performance Test - Add this to any page to test performance
(function() {
    'use strict';
    
    // Only run if explicitly enabled
    if (!window.location.search.includes('perf=1')) return;
    
    const perfTest = {
        marks: {},
        measures: [],
        
        mark(name) {
            this.marks[name] = performance.now();
            console.log(`⏱️ ${name}: ${this.marks[name].toFixed(0)}ms from page start`);
        },
        
        measure(name, start, end) {
            const startTime = this.marks[start] || 0;
            const endTime = end ? this.marks[end] : performance.now();
            const duration = endTime - startTime;
            
            this.measures.push({ name, duration, start: startTime, end: endTime });
            console.log(`📊 ${name}: ${duration.toFixed(0)}ms`);
            return duration;
        },
        
        networkAnalysis() {
            if (!performance.getEntriesByType) return;
            
            const resources = performance.getEntriesByType('resource');
            const images = resources.filter(r => 
                r.name.includes('cdn.pvpocket.xyz') || 
                r.name.includes('.png') || 
                r.name.includes('.jpg') ||
                r.name.includes('firebasestorage')
            );
            
            const apiCalls = resources.filter(r => r.name.includes('/api/'));
            
            console.log('\n🌐 Network Analysis:');
            console.log(`API calls: ${apiCalls.length}`);
            apiCalls.forEach(api => {
                console.log(`  ${api.name.split('/').pop()}: ${api.duration.toFixed(0)}ms`);
            });
            
            console.log(`Images loaded: ${images.length}`);
            const slowImages = images.filter(img => img.duration > 200);
            if (slowImages.length > 0) {
                console.log(`Slow images (>200ms): ${slowImages.length}`);
                slowImages.slice(0, 5).forEach(img => {
                    console.log(`  ${img.name.split('/').pop()}: ${img.duration.toFixed(0)}ms`);
                });
            }
        },
        
        domAnalysis() {
            console.log('\n📄 DOM Analysis:');
            console.log(`Total DOM nodes: ${document.querySelectorAll('*').length}`);
            console.log(`Images in DOM: ${document.images.length}`);
            console.log(`Card items: ${document.querySelectorAll('.card-item').length}`);
            console.log(`Loading cards: ${document.querySelectorAll('.is-loading').length}`);
        },
        
        report() {
            console.log('\n📈 PRODUCTION PERFORMANCE REPORT');
            console.log('='.repeat(50));
            
            const totalTime = performance.now();
            console.log(`Total time: ${totalTime.toFixed(0)}ms`);
            
            // Sort measures by duration
            const sorted = [...this.measures].sort((a, b) => b.duration - a.duration);
            
            console.log('\nSlowest operations:');
            sorted.slice(0, 8).forEach(m => {
                const percent = (m.duration / totalTime * 100).toFixed(1);
                console.log(`  ${m.name}: ${m.duration.toFixed(0)}ms (${percent}%)`);
            });
            
            this.networkAnalysis();
            this.domAnalysis();
            
            // Memory if available
            if (performance.memory) {
                console.log('\n💾 Memory:');
                console.log(`JS Heap: ${(performance.memory.usedJSHeapSize / 1048576).toFixed(1)}MB`);
            }
        }
    };
    
    // Auto-track key events
    perfTest.mark('script-start');
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            perfTest.mark('dom-ready');
            perfTest.measure('DOM parsing', 'script-start', 'dom-ready');
        });
    }
    
    window.addEventListener('load', () => {
        perfTest.mark('window-loaded');
        perfTest.measure('Full page load', 'script-start', 'window-loaded');
        
        // Report after a delay to catch async operations
        setTimeout(() => perfTest.report(), 2000);
    });
    
    // Make available globally
    window.perfTest = perfTest;
    
    console.log('🎯 Production Performance Test Active - Add ?perf=1 to URL');
})();