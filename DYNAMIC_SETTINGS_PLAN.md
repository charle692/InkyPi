# Dynamic Settings for Enhanced Preview

## Overview

This document outlines the plan for adding dynamic settings configuration to the enhanced preview page (`src/templates/enhanced_preview.html`). This feature will allow developers to modify plugin settings on-the-fly during development and see real-time preview updates, significantly improving the development workflow.

## Current Architecture Understanding

The enhanced preview system currently:
- Shows a static preview of a plugin with its existing settings
- Uses the plugin's saved settings from the device configuration
- Provides HTML/screenshot comparison views
- Has a link to the full settings page (`/plugin/{{ plugin_id }}`)

## Implementation Plan

### 1. Backend Changes - Enhanced API Endpoints

**File: `src/blueprints/dev_dashboard.py`**

Add new endpoints:

#### `GET /dev/enhanced-preview/<plugin_id>/settings`
- Returns plugin settings schema, current values, and defaults
- Response format:
```json
{
  "settings": { "current": "settings" },
  "schema": { "field": "definitions" },
  "defaults": { "default": "values" },
  "form_template": "<html>settings_form</html>"
}
```

#### `POST /dev/enhanced-preview/<plugin_id>/preview`
- Generates preview with temporary settings (doesn't save)
- Request body: `{ "settings": { "temporary": "settings" } }`
- Response: `{ "html": "<updated>preview</updated>" }`

#### `GET /dev/enhanced-preview/<plugin_id>/settings-form`
- Returns the plugin's settings form HTML for dynamic injection
- Leverages existing `settings.html` templates from plugins

### 2. Frontend Changes - Enhanced Preview UI

#### Template Changes: `src/templates/enhanced_preview.html`

Add a new collapsible settings panel in the sidebar:

```html
<div class="info-section">
  <h3>⚙️ Live Settings</h3>
  <div class="settings-controls">
    <button id="toggle-settings" class="toggle-btn">Show Settings</button>
    <div id="settings-actions" class="settings-actions" style="display: none;">
      <button id="reset-settings" class="action-link secondary">Reset</button>
      <button id="export-settings" class="action-link secondary">Export</button>
      <button id="import-settings" class="action-link secondary">Import</button>
    </div>
  </div>
  <div id="live-settings-container" class="live-settings" style="display: none;">
    <div class="loading-spinner"></div>
  </div>
</div>
```

#### JavaScript Changes: `src/static/js/enhanced_preview.js`

Extend the `EnhancedDevTools` class with new functionality:

```javascript
class EnhancedDevTools {
  constructor() {
    this.currentView = "html";
    this.currentSettings = {};
    this.originalSettings = {};
    this.previewUpdateDebounce = null;
    this.init();
  }

  // New methods to add:
  async loadSettingsForm() { /* Load settings form HTML */ }
  setupSettingsListeners() { /* Handle form changes */ }
  async updatePreview(newSettings) { /* Update preview with debounce */ }
  resetSettings() { /* Reset to original values */ }
  exportSettings() { /* Export settings as JSON */ }
  importSettings() { /* Import settings from JSON */ }
  validateSettings(settings) { /* Client-side validation */ }
}
```

#### CSS Changes: `src/static/css/enhanced_preview.css`

Add styling for the new settings panel:

```css
.live-settings {
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
  padding: 15px;
}

.settings-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.settings-actions {
  display: flex;
  gap: 5px;
}

.live-settings .form-group {
  margin-bottom: 12px;
}

.live-settings .form-input {
  width: 100%;
  padding: 6px 8px;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  font-size: 13px;
}
```

### 3. Settings Integration Strategy

#### Leverage Existing System
- **Reuse plugin `settings.html` templates** - No need to recreate forms
- **Extract form fields dynamically** - Parse existing HTML to identify settings
- **Use existing `pluginSettings` object pattern** - Maintain consistency
- **Apply same validation logic** - Reuse client-side validation from main settings

#### New Features Implementation
- **Real-time preview updates** - Debounced updates to prevent excessive API calls
- **Settings persistence during session** - Keep changes in memory only
- **Settings reset functionality** - Restore to saved values
- **Export/import settings** - Share configurations between developers
- **Settings validation** - Show errors and prevent invalid submissions

### 4. Implementation Phases

#### Phase 1: Basic Live Settings (MVP)
1. Add API endpoints for getting current settings and generating preview
2. Load plugin settings form into sidebar dynamically
3. Implement basic preview updates on form changes
4. Add loading states and basic error handling
5. Settings reset functionality

**Acceptance Criteria:**
- Developers can modify settings and see preview updates
- Settings changes don't persist to main configuration
- Reset button restores original values
- Basic validation prevents malformed requests

#### Phase 2: Enhanced User Experience
1. Add debounced updates (300ms delay) to prevent excessive API calls
2. Implement comprehensive settings validation and error display
3. Add export/import settings functionality
4. Optimize performance with better form handling
5. Add keyboard shortcuts for common actions
6. Improve loading states and error handling

**Acceptance Criteria:**
- Smooth performance with no laggy updates
- Clear error messages for invalid settings
- Settings can be exported/imported as JSON
- Keyboard shortcuts work consistently
- Professional loading states and transitions

#### Phase 3: Advanced Features
1. Settings presets for common configurations
2. Compare mode to see setting differences
3. Settings history with time travel (undo/redo)
4. Integration with existing live reload system
5. Settings bookmarking/favorites
6. Performance monitoring and optimization

**Acceptance Criteria:**
- Presets can be saved and applied quickly
- Side-by-side comparison shows setting differences
- Undo/redo works for entire session
- Seamless integration with existing live reload
- Settings can be bookmarked for quick access

### 5. Technical Implementation Details

#### Settings Loading Pattern
```javascript
async loadSettingsForm() {
  try {
    this.showLoading('live-settings-container');
    
    const response = await fetch(`/dev/enhanced-preview/${this.pluginId}/settings`);
    const { settings, schema, defaults, form_template } = await response.json();
    
    this.currentSettings = { ...settings };
    this.originalSettings = { ...settings };
    
    // Inject form HTML and setup listeners
    document.getElementById('live-settings-container').innerHTML = form_template;
    this.setupSettingsListeners();
    this.populateFormFields(settings);
    
  } catch (error) {
    this.showError('Failed to load settings', error);
  }
}
```

#### Live Preview Updates (Debounced)
```javascript
async updatePreview(newSettings) {
  // Clear existing debounce
  if (this.previewUpdateDebounce) {
    clearTimeout(this.previewUpdateDebounce);
  }
  
  // Set new debounce
  this.previewUpdateDebounce = setTimeout(async () => {
    try {
      this.showPreviewLoading();
      
      const response = await fetch(`/dev/enhanced-preview/${this.pluginId}/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ settings: newSettings })
      });
      
      const { html } = await response.json();
      document.querySelector('.device-frame').innerHTML = html;
      
      this.currentSettings = { ...newSettings };
      
    } catch (error) {
      this.showError('Failed to update preview', error);
    }
  }, 300); // 300ms debounce
}
```

#### Form Field Population
```javascript
populateFormFields(settings) {
  Object.keys(settings).forEach(key => {
    const field = document.getElementById(key) || document.querySelector(`[name="${key}"]`);
    if (!field) return;
    
    if (field.type === 'checkbox') {
      field.checked = settings[key] === 'true' || settings[key] === true;
    } else if (field.type === 'radio') {
      const radio = document.querySelector(`[name="${key}"][value="${settings[key]}"]`);
      if (radio) radio.checked = true;
    } else {
      field.value = settings[key];
    }
  });
}
```

#### Settings Validation
```javascript
validateSettings(settings) {
  const errors = [];
  
  // Basic validation rules
  if (settings.latitude && (isNaN(settings.latitude) || settings.latitude < -90 || settings.latitude > 90)) {
    errors.push('Latitude must be between -90 and 90');
  }
  
  if (settings.longitude && (isNaN(settings.longitude) || settings.longitude < -180 || settings.longitude > 180)) {
    errors.push('Longitude must be between -180 and 180');
  }
  
  // Plugin-specific validation would be handled by the backend
  return errors;
}
```

### 6. Benefits for Developers

1. **Rapid Iteration**: Test different settings combinations without leaving preview
2. **Configuration Testing**: Verify how settings affect plugin appearance immediately
3. **Development Workflow**: Streamlined develop → test → adjust cycle
4. **Collaboration**: Share specific configurations with team members via export/import
5. **Documentation**: Visual reference for different setting combinations
6. **Error Prevention**: Validation prevents invalid configurations
7. **Performance**: Debounced updates prevent system overload

### 7. Files to Modify

#### Backend Files
- `src/blueprints/dev_dashboard.py` - New API endpoints
- Potentially `src/plugins/base_plugin/base_plugin.py` - Settings schema extraction (optional)

#### Frontend Files
- `src/templates/enhanced_preview.html` - Settings panel UI
- `src/static/js/enhanced_preview.js` - Settings management logic
- `src/static/css/enhanced_preview.css` - Settings panel styling

#### Potential New Files
- `src/static/js/settings-manager.js` - Shared settings utilities (if patterns emerge)
- `src/tests/test_dev_dashboard.py` - Tests for new endpoints

### 8. Testing Strategy

#### Unit Tests
- API endpoints return correct data structures
- Settings validation works properly
- Form parsing handles various input types
- Error scenarios are handled gracefully

#### Integration Tests
- End-to-end settings update flow
- Multiple plugin types work correctly
- Performance under rapid setting changes
- Browser compatibility for form handling

#### User Acceptance Tests
- Developers can easily modify settings
- Preview updates are smooth and responsive
- Export/import functionality works
- Error messages are clear and helpful

### 9. Performance Considerations

- **Debouncing**: Prevent excessive API calls during rapid typing
- **Caching**: Cache settings forms to avoid repeated requests
- **Lazy Loading**: Load settings form only when requested
- **WebSocket Integration**: Consider WebSocket for real-time updates if performance issues arise
- **Form Optimization**: Use efficient event delegation for form handling

### 10. Security Considerations

- **Input Validation**: Server-side validation for all settings
- **XSS Prevention**: Properly escape all dynamic content
- **CSRF Protection**: Use CSRF tokens for settings updates
- **Rate Limiting**: Prevent abuse of preview generation endpoint
- **Data Exposure**: Ensure sensitive settings are not exposed inappropriately

## Conclusion

This implementation leverages the existing plugin architecture while providing developers with powerful real-time configuration capabilities. The phased approach ensures we deliver value quickly while building toward a comprehensive solution that significantly improves the plugin development workflow in InkyPi.

The modular design allows for incremental improvements and ensures the feature can evolve based on developer feedback and usage patterns.