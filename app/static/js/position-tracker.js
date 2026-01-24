// =====================================================
// ROBUST POSITION TRACKING SYSTEM
// Drop-in replacement for broken absolute positions
// =====================================================

/**
 * Position Anchor System
 * Uses DOM path + context instead of absolute positions
 * Works like ProseMirror but without rebuilding everything
 */
window.PositionTracker = {
    
    /**
     * Create a reliable anchor for selected text
     * Returns an anchor that survives edits
     */
    createAnchor: function(container, range) {
        const selectedText = range.toString().trim();
        
        // Get context around selection (50 chars before/after)
        const fullText = this._getFullText(container);
        const absolutePos = this._getAbsolutePosition(container, range.startContainer, range.startOffset);
        
        const beforeContext = fullText.substring(
            Math.max(0, absolutePos - 50), 
            absolutePos
        ).trim();
        
        const afterContext = fullText.substring(
            absolutePos + selectedText.length,
            absolutePos + selectedText.length + 50
        ).trim();
        
        // Create DOM path to anchor node
        const startPath = this._getNodePath(container, range.startContainer);
        const endPath = this._getNodePath(container, range.endContainer);
        
        // Generate unique fingerprint
        const fingerprint = this._generateFingerprint(selectedText, beforeContext, afterContext);
        
        return {
            text: selectedText,
            beforeContext: beforeContext,
            afterContext: afterContext,
            startPath: startPath,
            startOffset: range.startOffset,
            endPath: endPath,
            endOffset: range.endOffset,
            absolutePos: absolutePos,  // Backup for exact matches
            fingerprint: fingerprint,
            timestamp: new Date().toISOString()
        };
    },
    
    /**
     * Find position from anchor (even after edits)
     * Returns {node, offset, range, currentText} or null
     */
    findFromAnchor: function(container, anchor) {
        if (!anchor || !anchor.text) return null;
        
        // Strategy 1: Try exact position match first (fastest)
        const exactMatch = this._tryExactPosition(container, anchor);
        if (exactMatch) {
            console.log('✅ Found by exact position');
            return exactMatch;
        }
        
        // Strategy 2: Try DOM path (survives most edits)
        const pathMatch = this._tryDOMPath(container, anchor);
        if (pathMatch) {
            console.log('✅ Found by DOM path');
            return pathMatch;
        }
        
        // Strategy 3: Try context matching (handles moved text)
        const contextMatch = this._tryContextMatch(container, anchor);
        if (contextMatch) {
            console.log('✅ Found by context');
            return contextMatch;
        }
        
        // Strategy 4: Fuzzy text search (last resort)
        const fuzzyMatch = this._tryFuzzySearch(container, anchor);
        if (fuzzyMatch) {
            console.log('⚠️ Found by fuzzy search');
            return fuzzyMatch;
        }
        
        // Strategy 5: NEVER GIVE UP - Highlight whatever is there now
        // This ensures comment is always visible until deleted
        const fallbackMatch = this._tryFallbackHighlight(container, anchor);
        if (fallbackMatch) {
            console.log('🔄 Using fallback - highlighting current text at anchor location');
            return fallbackMatch;
        }
        
        console.log('❌ Anchor not found (rare - should not happen)');
        return null;
    },
    
    /**
     * Strategy 1: Try exact absolute position
     */
    _tryExactPosition: function(container, anchor) {
        const fullText = this._getFullText(container);
        const expectedText = fullText.substring(
            anchor.absolutePos,
            anchor.absolutePos + anchor.text.length
        );
        
        if (expectedText === anchor.text) {
            // Text still at exact position!
            return this._positionToRange(container, anchor.absolutePos, anchor.absolutePos + anchor.text.length);
        }
        
        return null;
    },
    
    /**
     * Strategy 2: Try DOM path
     */
    _tryDOMPath: function(container, anchor) {
        try {
            const startNode = this._getNodeFromPath(container, anchor.startPath);
            const endNode = this._getNodeFromPath(container, anchor.endPath);
            
            if (!startNode || !endNode) return null;
            
            // Verify text still matches
            const range = document.createRange();
            range.setStart(startNode, Math.min(anchor.startOffset, startNode.textContent.length));
            range.setEnd(endNode, Math.min(anchor.endOffset, endNode.textContent.length));
            
            const currentText = range.toString().trim();
            
            // Allow some variance (90% match)
            if (this._similarity(currentText, anchor.text) > 0.9) {
                return { range: range };
            }
        } catch (e) {
            // DOM path invalid
        }
        
        return null;
    },
    
    /**
     * Strategy 3: Context matching
     */
    _tryContextMatch: function(container, anchor) {
        const fullText = this._getFullText(container);
        
        // Find all occurrences of the text
        const occurrences = this._findAllOccurrences(fullText, anchor.text);
        
        if (occurrences.length === 0) return null;
        
        // Find best match by context
        let bestMatch = null;
        let bestScore = 0;
        
        for (const pos of occurrences) {
            const before = fullText.substring(Math.max(0, pos - 50), pos).trim();
            const after = fullText.substring(pos + anchor.text.length, pos + anchor.text.length + 50).trim();
            
            const beforeSim = this._similarity(before, anchor.beforeContext);
            const afterSim = this._similarity(after, anchor.afterContext);
            const score = (beforeSim + afterSim) / 2;
            
            if (score > bestScore) {
                bestScore = score;
                bestMatch = pos;
            }
        }
        
        // Need at least 60% context match
        if (bestScore > 0.6) {
            return this._positionToRange(container, bestMatch, bestMatch + anchor.text.length);
        }
        
        return null;
    },
    
    /**
     * Strategy 4: Fuzzy text search (for edited text)
     */
    _tryFuzzySearch: function(container, anchor) {
        const fullText = this._getFullText(container);
        
        // Try to find similar text
        const words = anchor.text.split(/\s+/);
        if (words.length < 2) return null;
        
        // Search for first and last word
        const firstWord = words[0];
        const lastWord = words[words.length - 1];
        
        const regex = new RegExp(`${this._escapeRegex(firstWord)}[\\s\\S]{0,100}${this._escapeRegex(lastWord)}`, 'i');
        const match = fullText.match(regex);
        
        if (match) {
            const pos = fullText.indexOf(match[0]);
            return this._positionToRange(container, pos, pos + match[0].length);
        }
        
        return null;
    },
    
    /**
     * Strategy 5: Fallback - Highlight whatever text is at anchor location
     * This ensures comments never disappear until explicitly deleted
     */
    _tryFallbackHighlight: function(container, anchor) {
        try {
            // Try to use DOM path to find approximate location
            const startNode = this._getNodeFromPath(container, anchor.startPath);
            
            if (startNode && startNode.textContent) {
                // Highlight whatever text is there now (same length as original)
                const currentText = startNode.textContent;
                const startOffset = Math.min(anchor.startOffset, currentText.length - 1);
                const length = Math.min(anchor.text.length, currentText.length - startOffset);
                
                if (length > 0) {
                    const range = document.createRange();
                    range.setStart(startNode, startOffset);
                    range.setEnd(startNode, startOffset + length);
                    
                    return {
                        range: range,
                        currentText: range.toString(),
                        modified: true  // Flag that text has been modified
                    };
                }
            }
            
            // If DOM path fails, use absolute position as last resort
            if (typeof anchor.absolutePos === 'number') {
                const length = anchor.text.length;
                const result = this._positionToRange(container, anchor.absolutePos, anchor.absolutePos + length);
                
                if (result && result.range) {
                    return {
                        range: result.range,
                        currentText: result.range.toString(),
                        modified: true
                    };
                }
            }
        } catch (e) {
            console.error('Fallback highlight error:', e);
        }
        
        return null;
    },
    
    /**
     * Helper: Get full text from container
     */
    _getFullText: function(container) {
        let text = '';
        const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, {
            acceptNode: function(node) {
                const parent = node.parentElement;
                if (parent && (
                    parent.classList.contains('comment-highlight') ||
                    parent.classList.contains('track-insert') ||
                    parent.classList.contains('track-delete') ||
                    parent.classList.contains('comment-icon')
                )) {
                    return NodeFilter.FILTER_REJECT;
                }
                return NodeFilter.FILTER_ACCEPT;
            }
        }, false);
        
        let node;
        while (node = walker.nextNode()) {
            text += node.textContent;
        }
        
        return text;
    },
    
    /**
     * Helper: Get absolute character position
     */
    _getAbsolutePosition: function(container, node, offset) {
        let position = 0;
        const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, null, false);
        
        let currentNode;
        while (currentNode = walker.nextNode()) {
            const parent = currentNode.parentElement;
            if (parent && (
                parent.classList.contains('comment-highlight') ||
                parent.classList.contains('track-insert') ||
                parent.classList.contains('track-delete') ||
                parent.classList.contains('comment-icon')
            )) continue;
            
            if (currentNode === node) {
                return position + offset;
            }
            position += currentNode.textContent.length;
        }
        
        return position;
    },
    
    /**
     * Helper: Get DOM path to node (like XPath)
     */
    _getNodePath: function(container, node) {
        const path = [];
        let current = node;
        
        while (current && current !== container) {
            const parent = current.parentNode;
            if (!parent) break;
            
            const index = Array.from(parent.childNodes).indexOf(current);
            path.unshift({
                tag: current.nodeName,
                index: index
            });
            
            current = parent;
        }
        
        return path;
    },
    
    /**
     * Helper: Get node from DOM path
     */
    _getNodeFromPath: function(container, path) {
        let current = container;
        
        for (const step of path) {
            if (!current.childNodes[step.index]) return null;
            current = current.childNodes[step.index];
        }
        
        return current;
    },
    
    /**
     * Helper: Convert absolute position to Range
     */
    _positionToRange: function(container, start, end) {
        const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, null, false);
        
        let currentPos = 0;
        let startNode = null, startOffset = 0;
        let endNode = null, endOffset = 0;
        let node;
        
        while (node = walker.nextNode()) {
            const parent = node.parentElement;
            if (parent && (
                parent.classList.contains('comment-highlight') ||
                parent.classList.contains('track-insert') ||
                parent.classList.contains('track-delete') ||
                parent.classList.contains('comment-icon')
            )) continue;
            
            const nodeLength = node.textContent.length;
            
            if (!startNode && start >= currentPos && start < currentPos + nodeLength) {
                startNode = node;
                startOffset = start - currentPos;
            }
            
            if (end >= currentPos && end <= currentPos + nodeLength) {
                endNode = node;
                endOffset = end - currentPos;
                break;
            }
            
            currentPos += nodeLength;
        }
        
        if (!startNode || !endNode) return null;
        
        try {
            const range = document.createRange();
            range.setStart(startNode, startOffset);
            range.setEnd(endNode, endOffset);
            return { range: range };
        } catch (e) {
            return null;
        }
    },
    
    /**
     * Helper: Find all occurrences of text
     */
    _findAllOccurrences: function(haystack, needle) {
        const positions = [];
        let pos = 0;
        
        while ((pos = haystack.indexOf(needle, pos)) !== -1) {
            positions.push(pos);
            pos += 1;
        }
        
        return positions;
    },
    
    /**
     * Helper: Calculate text similarity (0-1)
     */
    _similarity: function(s1, s2) {
        if (!s1 || !s2) return 0;
        if (s1 === s2) return 1;
        
        const longer = s1.length > s2.length ? s1 : s2;
        const shorter = s1.length > s2.length ? s2 : s1;
        
        if (longer.length === 0) return 1.0;
        
        const editDistance = this._levenshtein(longer, shorter);
        return (longer.length - editDistance) / longer.length;
    },
    
    /**
     * Helper: Levenshtein distance
     */
    _levenshtein: function(s1, s2) {
        const costs = [];
        for (let i = 0; i <= s1.length; i++) {
            let lastValue = i;
            for (let j = 0; j <= s2.length; j++) {
                if (i === 0) {
                    costs[j] = j;
                } else if (j > 0) {
                    let newValue = costs[j - 1];
                    if (s1.charAt(i - 1) !== s2.charAt(j - 1)) {
                        newValue = Math.min(Math.min(newValue, lastValue), costs[j]) + 1;
                    }
                    costs[j - 1] = lastValue;
                    lastValue = newValue;
                }
            }
            if (i > 0) costs[s2.length] = lastValue;
        }
        return costs[s2.length];
    },
    
    /**
     * Helper: Generate fingerprint hash
     */
    _generateFingerprint: function(text, before, after) {
        const combined = text + '|' + before + '|' + after;
        let hash = 0;
        for (let i = 0; i < combined.length; i++) {
            const char = combined.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash;
        }
        return Math.abs(hash).toString(36);
    },
    
    /**
     * Helper: Escape regex special chars
     */
    _escapeRegex: function(str) {
        return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }
};

console.log('✅ Position Tracker loaded');