# Decision Lab Integration

Decision Lab remains the explanatory layer for match recommendations. Formation Viewer
adds the visual layer beside it: Decision Lab explains the recommendation, while the
board shows the selected XI in a football context.

The integration rule is unchanged:

- the engine calculates;
- services map existing result data;
- Decision Lab and Formation Viewer interpret and display;
- neither layer changes engine probabilities, xG, tactics, orders, formations or lineup
  selection.

In the Match workspace, the recommendation summary and explanation stay above the local
result tabs. Formation Board becomes the default visualization tab, with Comparison and
Detailed XI preserved for detailed review.
