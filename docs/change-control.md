# Cost and deployment change control

The target is CAD $0 out of pocket. This PR performs offline validation only and does not deploy, log in to Azure, or consume subscription credits. Existing subscription charges are not verified by CI.

Before any deployment, obtain Rob's explicit approval for the exact resource changes, current CAD pricing, subscription credit/expiry status, maximum possible out-of-pocket exposure, and cleanup plan. Do not assume credits or a free-tier label guarantee zero charges. A budget alert is not a spending cap.

No automated Azure deployment workflow or Azure credentials are configured by this change. Keep that boundary unless separately authorized. Validate locally with `python checks/check_network.py` and `python -m unittest discover -s checks -v`.

The baseline permits VNet traffic through default NSG rules. Private subnets disable default outbound access; they do not establish isolation between application, management, and server roles. Use the segmentation design as a proposal requiring review and testing before deployment.
