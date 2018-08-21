package sandcrawler

import java.io.InputStream

import scala.io.Source
import scala.util.parsing.json.JSONObject

object ScorableFeatures {
  // TODO: Add exception handling.
  val fileStream : InputStream = getClass.getResourceAsStream("/slug-blacklist.txt")
  val SlugBlacklist : Set[String] = Source.fromInputStream(fileStream).getLines.toSet
  fileStream.close

  // Static factory method
  def create(title : String, year : Int = 0, doi : String = "", sha1 : String = "") : ScorableFeatures = {
    new ScorableFeatures(
      title=if (title == null) "" else title,
      year=year,
      doi=if (doi == null) "" else doi,
      sha1=if (sha1 == null) "" else sha1)
  }
}

// Contains features needed to make slug and to score (in combination
// with a second ScorableFeatures). Create with above static factory method.
class ScorableFeatures private(title : String, year: Int = 0, doi : String = "", sha1: String = "") {

  def toMap() : Map[String, Any] =
    Map("title" -> title, "year" -> year, "doi" -> doi, "sha1" -> sha1)

  override def toString() : String =
    JSONObject(toMap).toString

  def toSlug() : String = {
    if (title == null) {
      Scorable.NoSlug
    } else {
      val unaccented = StringUtilities.removeAccents(title)
      // Remove punctuation
      val slug = StringUtilities.removePunctuation((unaccented.toLowerCase())).replaceAll("\\s", "")
      if (slug.isEmpty || slug == null || (ScorableFeatures.SlugBlacklist contains slug)) Scorable.NoSlug else slug
    }
  }

  def toMapFeatures : MapFeatures =
    MapFeatures(toSlug, toString)
}
