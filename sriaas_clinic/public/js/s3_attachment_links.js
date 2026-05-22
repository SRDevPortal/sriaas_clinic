// Shared S3 attachment opener for forms that store File.file_url as s3://...

window.sriaas_intercept_s3_attachments = function (frm) {
  if (!frm || !frm.wrapper) return;

  setTimeout(() => {
    const $wrapper = $(frm.wrapper);

    $wrapper.off('click.sriaas_s3_presign').on(
      'click.sriaas_s3_presign',
      'a[href]',
      function (e) {
        const href = $(this).attr('href');
        if (!href) return;

        if (href.startsWith('s3://') || href.includes('amazonaws.com')) {
          e.preventDefault();
          e.stopPropagation();

          frappe.call({
            method: 'sriaas_clinic.api.s3.presign.get_presigned_url',
            args: { file_url: href },
            callback(r) {
              if (typeof r.message === 'string') {
                window.open(r.message, '_blank');
              } else {
                frappe.msgprint(__('Could not generate secure file link.'));
              }
            }
          });
        }
      }
    );
  }, 500);
};
