install:
	pip3 install requirements.txt

download: dl_fedora_bugs dl_debian_pkgs dl_debian_bugs dl_fedora_pkgs dl_debian_patches dl_fedora_patches

dl_fedora_pkgs:
	$(info Starting to download packages from Fedora...)
	python3 fedora.py fetch pkgs
dl_fedora_bugs:
	$(info Starting to download bugs from Fedora...)
	python3 fedora.py fetch bugs
dl_fedora_patches:
	$(info Starting to download patches from Fedora...)
	python3 fedora.py fetch patches
dl_debian_pkgs:
	$(info Starting to download packages from Debian...)
	python3 debian.py fetch pkgs
dl_debian_bugs:
	$(info Starting to download bugs from Debian...)
	python3 debian.py fetch bugs
dl_debian_patches:
	$(info Starting to download patches from Debian...)
	python3 debian.py fetch patches

mark-upstream: mark_uf_debian_bugs mark_uf_fedora_bugs 

mark_uf_fedora_bugs:
	$(info Starting to mark upstream-fixed bugs in Fedora...)
	python3 fedora.py mark upstream_fixed
mark_uf_debian_bugs:
	$(info Starting to mark upstream-fixed bugs in Debian...)
	python3 debian.py mark upstream_fixed

mark-local-fixes: mark_lf_fedora_bugs
mark_lf_fedora_bugs:
	$(info Starting to mark locally-fixed bugs in Fedora...)
	python3 fedora.py fetch attachments
	python3 fedora.py mark local_fixed

mark_lf_debian_bugs:
	$(info Starting to mark locally-fixed bugs in Debian...)
	python3 debian.py mark local_fixed

mapping: map_pkg_category rm_fedora_dup_bugs rm_debian_dup_bugs
map_pkg_category:
	python3 fedora.py map pkg_category
rm_fedora_dup_bugs:
	python3 fedora.py remove duplicate_ids
rm_debian_dup_bugs:
	python3 debian.py remove duplicate_ids