// Chrome and Edge: the toolbar button opens the side panel. Safari has no side panel: use a popup.
if (chrome.sidePanel && chrome.sidePanel.setPanelBehavior) {
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(() => {});
} else if (chrome.action && chrome.action.setPopup) {
  chrome.action.setPopup({ popup: 'panel.html' });
}
