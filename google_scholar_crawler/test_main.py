from bs4 import BeautifulSoup

import main
from main import parse_author_profile, parse_publications


PROFILE_HTML = """
<html>
  <body>
    <div id="gsc_prf_in">Lijun An</div>
    <div id="gsc_prf_i">
      <div class="gsc_prf_il">Postdoctoral Fellow, Lund University</div>
      <div class="gsc_prf_il">Verified email at med.lu.se</div>
      <a href="https://example.com">Homepage</a>
    </div>
    <div id="gsc_prf_int">
      <a>Machine learning</a>
      <a>Neuroimaging</a>
    </div>
    <table id="gsc_rsb_st">
      <tbody>
        <tr>
          <td class="gsc_rsb_sc1">Citations</td>
          <td class="gsc_rsb_std">1,234</td>
          <td class="gsc_rsb_std">999</td>
        </tr>
        <tr>
          <td class="gsc_rsb_sc1">h-index</td>
          <td class="gsc_rsb_std">25</td>
          <td class="gsc_rsb_std">20</td>
        </tr>
        <tr>
          <td class="gsc_rsb_sc1">i10-index</td>
          <td class="gsc_rsb_std">30</td>
          <td class="gsc_rsb_std">28</td>
        </tr>
      </tbody>
    </table>
    <span class="gsc_g_t">2025</span>
    <span class="gsc_g_t">2026</span>
    <span class="gsc_g_al">42</span>
    <span class="gsc_g_al">87</span>
  </body>
</html>
"""


PUBLICATIONS_HTML = """
<html>
  <body>
    <table>
      <tr class="gsc_a_tr">
        <td class="gsc_a_t">
          <a class="gsc_a_at" href="/citations?view_op=view_citation&hl=en&user=La_luGsAAAAJ&citation_for_view=La_luGsAAAAJ:abc123">Example Paper</a>
          <div class="gs_gray">A Author, L An</div>
          <div class="gs_gray">Nature Medicine, 2026</div>
        </td>
        <td class="gsc_a_c"><a class="gsc_a_ac">1,234</a></td>
        <td class="gsc_a_y"><span class="gsc_a_h">2026</span></td>
      </tr>
      <tr class="gsc_a_tr">
        <td class="gsc_a_t">
          <a class="gsc_a_at" href="/citations?view_op=view_citation&hl=en&user=La_luGsAAAAJ&citation_for_view=La_luGsAAAAJ:no_cites">No Citation Paper</a>
          <div class="gs_gray">L An</div>
          <div class="gs_gray">Preprint</div>
        </td>
        <td class="gsc_a_c"><a class="gsc_a_ac"></a></td>
        <td class="gsc_a_y"><span class="gsc_a_h">2025</span></td>
      </tr>
    </table>
  </body>
</html>
"""


def test_parse_author_profile_reads_metrics_and_metadata():
    soup = BeautifulSoup(PROFILE_HTML, "html.parser")

    author = parse_author_profile(soup)

    assert author["name"] == "Lijun An"
    assert author["affiliation"] == "Postdoctoral Fellow, Lund University"
    assert author["email_domain"] == "med.lu.se"
    assert author["interests"] == ["Machine learning", "Neuroimaging"]
    assert author["citedby"] == 1234
    assert author["citedby5y"] == 999
    assert author["hindex"] == 25
    assert author["i10index5y"] == 28
    assert author["cites_per_year"] == {"2025": 42, "2026": 87}


def test_parse_publications_reads_ids_and_citation_counts():
    soup = BeautifulSoup(PUBLICATIONS_HTML, "html.parser")

    publications = parse_publications(soup)

    assert publications["La_luGsAAAAJ:abc123"]["num_citations"] == 1234
    assert publications["La_luGsAAAAJ:abc123"]["bib"]["title"] == "Example Paper"
    assert publications["La_luGsAAAAJ:abc123"]["bib"]["pub_year"] == "2026"
    assert publications["La_luGsAAAAJ:no_cites"]["num_citations"] == 0


def test_build_remote_stats_url_uses_repository_env(monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")

    url = main.build_remote_stats_url("gs_data.json")

    assert url == (
        "https://raw.githubusercontent.com/owner/repo/"
        "google-scholar-stats/gs_data.json"
    )


def test_read_previous_author_prefers_local_cache(tmp_path, monkeypatch):
    cache_path = tmp_path / "gs_data.json"
    cache_path.write_text('{"name": "local", "citedby": 10}', encoding="utf-8")
    monkeypatch.setattr(main, "GS_DATA_PATH", cache_path)
    monkeypatch.setattr(
        main,
        "read_remote_json",
        lambda filename: {"name": "remote", "citedby": 20},
    )

    assert main.read_previous_author() == {"name": "local", "citedby": 10}


def test_read_previous_author_falls_back_to_stats_branch(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "GS_DATA_PATH", tmp_path / "missing.json")
    monkeypatch.setattr(
        main,
        "read_remote_json",
        lambda filename: {"name": "remote", "citedby": 20},
    )

    assert main.read_previous_author() == {"name": "remote", "citedby": 20}
